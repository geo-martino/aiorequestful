"""
All operations relating to handling of requests to an HTTP service.

This is the core module for handling requests and their responses
including using authorisation and caching as necessary.
"""
from __future__ import annotations

import contextlib
import inspect
import json
import logging
from collections.abc import Mapping, Callable, Sequence
from copy import deepcopy
from http import HTTPMethod
from typing import Any, Self, Unpack
from urllib.parse import unquote

import aiohttp
from yarl import URL

from aiorequestful._utils import format_url_log
from aiorequestful.auth import Authoriser
from aiorequestful.cache.backend import ResponseCache
from aiorequestful.cache.session import CachedSession
from aiorequestful.exception import RequestError
from aiorequestful.response.payload import StringPayloadHandler, PayloadHandler
from aiorequestful.response.status import StatusHandler, ClientErrorStatusHandler, UnauthorisedStatusHandler, \
    RateLimitStatusHandler
from aiorequestful.timer import Timer
from aiorequestful.types import URLInput, Headers, MethodInput, RequestKwargs

_DEFAULT_RESPONSE_HANDLERS = [
    UnauthorisedStatusHandler(), RateLimitStatusHandler(), ClientErrorStatusHandler()
]


class RequestHandler[A: Authoriser, P: Any]:
    """
    Generic HTTP request handler.
    Handles error responses, retries on failed requests, authorisation, caching etc.

    :param connector: When called, returns a new session to use when making requests.
    :param authoriser: The authoriser to use when authorising requests to the HTTP service.
    :param payload_handler: Handles payload data conversion to return response payload in expected format.
    :param response_handlers: Handlers to handle responses for specific status codes.
        Should many of the given handlers be responsible for handling the same status code,
        the first handler in the sequence will be used for that status code.
    :param wait_timer: The time to wait after every request, regardless of whether it was successful.
        It is best practice to configure this such that a maximum time can be achieved
        within a reasonable time to ensure times between requests do not get too large.
        Useful to help manage calls to services that have strict restraints around rate limiting.
    :param retry_timer: The timer that controls how long to wait in between each successive failed request.
        It is best practice to configure this such that a maximum time can be achieved
        within a reasonable time to cause a timeout and raise an exception.
    """

    __slots__ = (
        "logger",
        "_connector",
        "_session",
        "authoriser",
        "_payload_handler",
        "_response_handlers",
        "wait_timer",
        "_retry_timer",
        "_retry_logged",
    )

    @property
    def closed(self):
        """Is the stored client session closed."""
        return self._session is None or self._session.closed

    @property
    def session(self) -> aiohttp.ClientSession:
        """The :py:class:`ClientSession` object if it exists and is open."""
        if not self.closed:
            return self._session

    @property
    def payload_handler(self) -> PayloadHandler:
        """Handles a response according to its status, payload, headers, etc."""
        return self._payload_handler

    @payload_handler.setter
    def payload_handler(self, value: PayloadHandler):
        self._payload_handler = value

        if isinstance(self._session, CachedSession):
            for repository in self._session.cache.values():
                # all repositories must use the same payload handler as the request handler
                # for it to function correctly
                repository.settings.payload_handler = self._payload_handler

    @property
    def response_handlers(self) -> dict[int, StatusHandler]:
        """Handles a response according to its status, payload, headers, etc."""
        return self._response_handlers

    @response_handlers.setter
    def response_handlers(self, value: Sequence[StatusHandler]):
        self._response_handlers.update({
            status: handler for handler in reversed(value) for status in handler.status_codes
        })

    @property
    def retry_timer(self) -> Timer | None:
        """
        The timer that controls how long to wait in between each successive failed request.
        Always returns a reset timer with initial settings.
        """
        if not self._retry_timer:
            return
        return deepcopy(self._retry_timer)

    @retry_timer.setter
    def retry_timer(self, value: Timer | None):
        self._retry_timer = value

    @classmethod
    def create(
            cls,
            authoriser: A | None = None,
            cache: ResponseCache | None = None,
            payload_handler: PayloadHandler[P] = None,
            response_handlers: Sequence[StatusHandler] = (),
            wait_timer: Timer = None,
            retry_timer: Timer = None,
            **session_kwargs
    ) -> RequestHandler[A, P]:
        """Create a new :py:class:`RequestHandler` with an appropriate session ``connector`` given the input kwargs"""
        def connector() -> aiohttp.ClientSession:
            """Create an appropriate session ``connector`` given the input kwargs"""
            if cache is not None:
                return CachedSession(cache=cache, **session_kwargs)
            return aiohttp.ClientSession(**session_kwargs)

        return cls(
            connector=connector,
            authoriser=authoriser,
            payload_handler=payload_handler,
            response_handlers=response_handlers,
            wait_timer=wait_timer,
            retry_timer=retry_timer,
        )

    def __init__(
            self,
            connector: Callable[[], aiohttp.ClientSession],
            authoriser: A | None = None,
            payload_handler: PayloadHandler = None,
            response_handlers: Sequence[StatusHandler] = (),
            wait_timer: Timer = None,
            retry_timer: Timer = None,
    ):
        #: The :py:class:`logging.Logger` for this  object
        self.logger: logging.Logger = logging.getLogger(__name__)

        self._connector = connector
        self._session: aiohttp.ClientSession | CachedSession | None = None

        #: The :py:class:`Authoriser` object
        self.authoriser = authoriser

        #: Handles payload data conversion to return response payload in expected format
        self.payload_handler = payload_handler if payload_handler is not None else StringPayloadHandler()

        self._response_handlers = {}
        self.response_handlers = response_handlers if response_handlers is not None else _DEFAULT_RESPONSE_HANDLERS

        #: The time to wait after every request, regardless of whether it was successful
        self.wait_timer = wait_timer
        self._retry_timer = retry_timer

        self._retry_logged = False

    async def __aenter__(self) -> Self:
        self._retry_logged = False

        if self.closed:
            self._session = self._connector()

        # force setting payload handler on all cache repositories
        self.payload_handler = self.payload_handler

        await self.session.__aenter__()
        await self.authorise()

        return self

    async def __aexit__(self, __exc_type, __exc_value, __traceback) -> None:
        if self._session is not None:
            await self._session.__aexit__(__exc_type, __exc_value, __traceback)
            self._session = None

        self._retry_logged = False

    async def authorise(self) -> Headers:
        """
        Authenticate and authorise, testing/refreshing/re-authorising as needed.
        Updates the session with new credentials.

        :return: Headers for request authorisation.
        :raise AuthoriserError: If the token cannot be validated.
        """
        if self.closed:
            raise RequestError("Session is closed. Enter this object's context to start a new session.")

        headers = {}
        if self.authoriser is not None:
            self.session.headers.update(await self.authoriser)

        return headers

    async def close(self) -> None:
        """Close the current session. No more requests will be possible once this has been called."""
        await self.session.close()

    def log(
            self, method: str, url: URLInput, message: str | list = None, level: int = logging.DEBUG, **kwargs
    ) -> None:
        """Format and log a request or request adjacent message to the given ``level``."""
        log: list[Any] = []

        url = URL(url)
        if url.query:
            log.extend(f"{k}: {unquote(v):<4}" for k, v in sorted(url.query.items()))
        if kwargs.get("params"):
            log.extend(f"{k}: {v:<4}" for k, v in sorted(kwargs.pop("params").items()))
        if kwargs.get("json"):
            log.extend(f"{k}: {str(v):<4}" for k, v in sorted(kwargs.pop("json").items()))
        if len(kwargs) > 0:
            log.extend(f"{k.title()}: {str(v):<4}" for k, v in kwargs.items() if v)
        if message:
            log.append(message) if isinstance(message, str) else log.extend(message)

        self.logger.log(level=level, msg=format_url_log(method=method, url=url, messages=log))

    async def request(self, method: MethodInput, url: URLInput, **kwargs: Unpack[RequestKwargs]) -> P:
        """
        Generic method for handling HTTP requests handling errors, authorisation, backoff, caching etc. as configured.
        See :py:func:`request` for more arguments.

        :param method: HTTP request method (such as GET, POST, PUT, etc.)
        :param url: The URL to perform the request on.
        :return: The JSON formatted response or, if JSON formatting not possible, the text response.
        :raise RequestError: For any request which fails.
        :raise ResponseError: For any request which returns an invalid response.
        :raise StatusHandlerError: For any request which returns a response with a status that could not be handled.
        """
        if self.closed:
            raise RequestError(
                "Could not send a request as the session is closed. "
                "Enter the RequestHandler's context to start a new session."
            )

        method = HTTPMethod(method.upper())
        retry_timer = self.retry_timer

        while True:
            async with self._request(method=method, url=url, **kwargs) as response:
                if response is None:
                    raise RequestError("No response received")

                if await self._handle_response(response, retry_timer=retry_timer):
                    continue

                if response.ok:
                    payload: P = await self.payload_handler(response)
                    break

                await self._log_response(response=response, method=method, url=url)
                await self._handle_retry_timer(method=method, url=url, timer=retry_timer)

        self._retry_logged = False
        return payload

    @contextlib.asynccontextmanager
    async def _request(
            self,
            method: HTTPMethod,
            url: URLInput,
            log_message: str | list[str] = None,
            **kwargs
    ) -> aiohttp.ClientResponse | None:
        """Handle logging a request, send the request, and return the response"""
        if isinstance(log_message, str):
            log_message = [log_message]
        elif log_message is None:
            log_message = []

        if isinstance(self.session, CachedSession):
            log_message.append("Cached Request")
        self.log(method=method.name, url=url, message=log_message, **kwargs)

        if not isinstance(self.session, CachedSession):
            self._clean_requests_kwargs(kwargs)
        if "headers" in kwargs:
            kwargs["headers"].update(self.session.headers)

        try:
            async with self.session.request(method=method.name, url=url, **kwargs) as response:
                yield response
                if self.wait_timer is not None:
                    await self.wait_timer
        except aiohttp.ClientError as ex:
            self.logger.debug(str(ex))
            yield

    @staticmethod
    def _clean_requests_kwargs(kwargs: dict[str, Any]) -> None:
        """Clean ``kwargs`` by removing any kwarg not in the signature of the :py:meth:`aiohttp.request` method."""
        signature = inspect.signature(aiohttp.request).parameters
        for key in list(kwargs):
            if key not in signature:
                kwargs.pop(key)

    async def _log_response(self, response: aiohttp.ClientResponse, method: HTTPMethod, url: URLInput) -> None:
        """Log the method, URL, response text, and response headers."""
        response_headers = response.headers
        if isinstance(response.headers, Mapping):  # format headers if JSON
            response_headers = json.dumps(dict(response.headers), indent=2)
        self.log(
            method=method.name,
            url=url,
            message=[
                f"Status code: {response.status}",
                "Response text and headers follow:\n"
                f"Response text:\n\t{(await response.text()).replace("\n", "\n\t")}\n"
                f"Headers:\n\t{response_headers.replace("\n", "\n\t")}"
                f"\33[0m"
            ]
        )

    async def _handle_response(self, response: aiohttp.ClientResponse, retry_timer: Timer | None = None) -> bool:
        if response.status not in self.response_handlers:
            return False

        response_handler: StatusHandler = self.response_handlers[response.status]
        return await response_handler(
            response=response,
            authoriser=self.authoriser,
            session=self.session,
            payload_handler=self.payload_handler,
            wait_timer=self.wait_timer,
            retry_timer=retry_timer,
        )

    async def _handle_retry_timer(self, method: HTTPMethod, url: URLInput, timer: Timer | None) -> None:
        if timer is None or not timer.can_increase:
            raise RequestError("Max retries exceeded")

        if not self._retry_logged:
            self.logger.warning(
                f"\33[93mRequest failed. Will retry request {timer.count_remaining} more times "
                f"and timeout in {timer.total_remaining:.2f} seconds...\33[0m"
            )
            self._retry_logged = True

        self.log(
            method=method.name,
            url=url,
            message=f"Request failed: retrying in {int(timer):.2f} seconds..."
        )
        await timer
        timer.increase()

    async def get(self, url: URLInput, **kwargs) -> P:
        """Sends a GET request."""
        kwargs.pop("method", None)
        return await self.request("get", url=url, **kwargs)

    async def post(self, url: URLInput, **kwargs) -> P:
        """Sends a POST request."""
        kwargs.pop("method", None)
        return await self.request("post", url=url, **kwargs)

    async def put(self, url: URLInput, **kwargs) -> P:
        """Sends a PUT request."""
        kwargs.pop("method", None)
        return await self.request("put", url=url, **kwargs)

    async def delete(self, url: URLInput, **kwargs) -> P:
        """Sends a DELETE request."""
        kwargs.pop("method", None)
        return await self.request("delete", url, **kwargs)

    async def options(self, url: URLInput, **kwargs) -> P:
        """Sends an OPTIONS request."""
        kwargs.pop("method", None)
        return await self.request("options", url=url, **kwargs)

    async def head(self, url: URLInput, **kwargs) -> P:
        """Sends a HEAD request."""
        kwargs.pop("method", None)
        kwargs.setdefault("allow_redirects", False)
        return await self.request("head", url=url, **kwargs)

    async def patch(self, url: URLInput, **kwargs) -> P:
        """Sends a PATCH request."""
        kwargs.pop("method", None)
        return await self.request("patch", url=url, **kwargs)

    def __copy__(self):
        """Do not copy handler"""
        return self

    def __deepcopy__(self, _: dict = None):
        """Do not copy handler"""
        return self
