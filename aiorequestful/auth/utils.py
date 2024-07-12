"""
Authoriser specific utilities which can be used to build implementations of authoriser flows.
"""
import json
import logging
import os
import socket
from collections.abc import MutableMapping, Generator, Coroutine, Callable, Awaitable, Mapping
from contextlib import contextmanager, asynccontextmanager
from copy import deepcopy
from datetime import datetime
from http import HTTPMethod
from pathlib import Path
from typing import Any, Literal, Unpack

from aiohttp import ClientSession, ClientResponse
from yarl import URL

from aiorequestful.auth.exception import AuthoriserError
from aiorequestful.types import MethodInput, URLInput, Headers, ImmutableHeaders, MutableJSON, ImmutableJSON, \
    JSON, RequestKwargs


class AuthRequest:
    """
    Request handler for sending authentication and authorisation requests.
    Supply this class with the required arguments for your request.

    :param method: HTTP request method (such as GET, POST, PUT, etc.).
    :param url: The URL of the request.
    :param kwargs: Any other kwargs required for a successful request.
        Arguments passed through to `.aiohttp.ClientSession.request`.
        See aiohttp reference for more info on available kwargs:
        https://docs.aiohttp.org/en/stable/client_reference.html#aiohttp.ClientSession.request
    """

    __slots__ = tuple(list(RequestKwargs.__annotations__))

    def __init__(self, method: MethodInput, url: URLInput, **kwargs: Unpack[RequestKwargs]):
        self.method = HTTPMethod(method.upper())
        self.url = URL(url)

        for k, v in kwargs.items():
            setattr(self, k, v)

    @classmethod
    def _sanitise_kwargs(cls, kwargs: MutableMapping[str, Any]) -> None:
        cls._sanitise_map(kwargs.get("params"))
        cls._sanitise_map(kwargs.get("data"))

    @classmethod
    def _sanitise_map(cls, value: MutableMapping[str, Any] | None) -> None:
        if not value:
            return

        for k, v in value.items():
            if isinstance(v, MutableMapping):
                cls._sanitise_map(v)
            elif isinstance(v, bool) or not isinstance(v, str | int | float):
                value[k] = json.dumps(v)

    @contextmanager
    def enrich_parameters(
            self, key: Literal["data", "params", "json", "headers"], value: dict[str, Any]
    ) -> Generator[None, None, None]:
        """
        Temporarily append data to the parameters of a request within a context,
        removing them when no longer in context.

        :param key: The keyword of the argument to append data to.
        :param value: The value to append.
        """
        if not value:
            yield
            return

        current_value = getattr(self, key, {})
        setattr(self, key, current_value | value)

        yield

        if current_value:
            setattr(self, key, current_value)
        else:
            delattr(self, key)

    def __call__(self, session: ClientSession) -> Coroutine[ClientResponse, None, None]:
        return self.request(session=session)

    @asynccontextmanager
    async def request(self, session: ClientSession) -> Coroutine[ClientResponse, None, None]:
        """Send the request within the given ``session`` and return the response."""
        kwargs = {
            key: deepcopy(getattr(self, key)) for key in self.__slots__
            if key not in ("method", "url") and hasattr(self, key)
        }
        self._sanitise_kwargs(kwargs)

        async with session.request(method=self.method.name, url=self.url, **kwargs) as response:
            yield response


class AuthResponse(MutableMapping[str, Any]):
    """
    Handle saving, loading, enriching, sanitising etc. of responses.
    Also handles token extraction and header generation from token responses.

    :param file_path: Path to use for loading and saving a token.
    :param token_prefix_default: Prefix to add to the header value for authorised calls to an endpoint.
    :param additional_headers: Extra headers to add to the final headers to ensure future successful requests.
    """

    __slots__ = (
        "logger",
        "_response",
        "file_path",
        "token_key",
        "token_prefix_default",
        "additional_headers",
    )

    @property
    def token(self) -> str | None:
        """Extract the token from the stored response."""
        if not self:
            raise AuthoriserError("Stored response is not available.")

        if self.token_key not in self:
            raise AuthoriserError(
                f"Did not find valid token at key: {self.token_key} | {self.sanitised}"
            )
        return str(self[self.token_key])

    @property
    def headers(self) -> Headers:
        """Generate headers from the stored response, adding all additional headers as needed."""
        if not self:
            return {}

        header_key = "Authorization"
        header_prefix = self.get("token_type", self.token_prefix_default)

        headers = {header_key: f"{header_prefix} {self.token}"}
        if self.additional_headers:
            headers.update(self.additional_headers)
        return headers

    @property
    def sanitised(self) -> JSON:
        """
        Returns a reformatted response, making it safe to log by removing sensitive values at predefined keys.
        """
        if not self:
            return {}

        def _clean_value(value: Any) -> str:
            value = str(value)
            if len(value) < 5:
                return ""
            return f"{value[:5]}..."

        response_clean = {k: _clean_value(v) if str(k).endswith("_token") else v for k, v in self.items()}
        if self.token_key in response_clean:
            response_clean[self.token_key] = _clean_value(response_clean[self.token_key])

        return response_clean

    def __init__(
            self,
            file_path: str | Path = None,
            token_prefix_default: str | None = None,
            additional_headers: ImmutableHeaders = None,
    ):
        #: The :py:class:`logging.Logger` for this  object
        self.logger: logging.Logger = logging.getLogger(__name__)

        #: Stores the currently valid response
        self._response: MutableJSON = {}

        #: Path to use for loading and saving a token.
        self.file_path: Path | None = Path(file_path).with_suffix(".json") if file_path else None
        #: Prefix to add to the header value for authorised calls to an endpoint.
        self.token_key: str = "access_token"
        #: The default prefix to append to the credentials in the 'Authorization' header value
        #: if one cannot be found in the response.
        self.token_prefix_default: str | None = token_prefix_default

        #: Extra headers to add to the final headers to ensure future successful requests.
        self.additional_headers = additional_headers

    def __getitem__(self, __key):
        return self._response[__key]

    def __setitem__(self, __key, __value):
        self._response[__key] = __value

    def __delitem__(self, __key):
        del self._response[__key]

    def __len__(self):
        return len(self._response)

    def __iter__(self):
        return iter(self._response)

    def replace(self, response: Mapping[str, Any]) -> None:
        """Replace the currently stored response with a new ``response``"""
        self.clear()
        self.update(response)

    def enrich(self, refresh_token: str = None) -> None:
        """
        Extends the response by adding granted and expiry time information to it.
        Adds the given ``refresh_token`` to the response if one is not present.
        """
        if not self:
            return

        # add granted and expiry times to token
        self["granted_at"] = datetime.now().timestamp()
        if "expires_in" in self:
            expires_at = self["granted_at"] + float(self["expires_in"])
            self["expires_at"] = expires_at

        # request usually does return a new refresh token, but add the previous one if not
        if "refresh_token" not in self and refresh_token:
            self["refresh_token"] = refresh_token

    def load_response_from_file(self) -> JSON | None:
        """Load a stored response from given path"""
        if not self.file_path or not self.file_path.exists():
            return

        self.logger.debug("Saved authorisation code response found. Loading...")
        with open(self.file_path, "r") as file:  # load token
            self._response = json.load(file)

        return self._response

    def save_response_to_file(self) -> None:
        """Save the stored response to the stored file path."""
        if not self.file_path or not self:
            return

        os.makedirs(self.file_path.parent, exist_ok=True)

        self.logger.debug(f"Saving authorisation code response: {self.sanitised}")
        with open(self.file_path, "w") as file:
            json.dump(self._response, file, indent=2)


class AuthTester:
    """
    Run tests against the response of authorisation request to ensure its validity.

    When setting ``max_expiry``, the following example illustrates how this is used:
        * A token has 600 second total expiry time,
        * it is 60 seconds old and therefore still has 540 seconds of authorised time left,
        * you set ``max_expiry`` = 300, the token will pass tests.
        * The same token is tested again later when it is 500 now seconds old,
        * it now has only 100 seconds of authorised time left,
        * it will now fail the tests as 100 < 300.

    :param request: The request to execute when testing the access token.
    :param response_test: Test to apply to the response from the access token request.
    :param max_expiry: The max allowed time in seconds left until the token is due to expire.
        Useful for ensuring the token will be valid for long enough to run your operations.
    """

    __slots__ = ("logger", "request", "response_test", "max_expiry")

    def __init__(
            self,
            request: AuthRequest | None = None,
            response_test: Callable[[ClientResponse], Awaitable[bool]] | None = None,
            max_expiry: int = 0,
    ):
        #: The :py:class:`logging.Logger` for this  object
        self.logger: logging.Logger = logging.getLogger(__name__)

        #: The request to execute when testing the access token.
        self.request = request
        #: Test to apply to the response from the access token request.
        self.response_test = response_test
        #: The max allowed time in seconds left until the token is due to expire
        self.max_expiry = max_expiry

    def __call__(self, response: AuthResponse | None = None) -> Awaitable[bool]:
        return self.test(response=response)

    async def test(self, response: AuthResponse | None = None) -> bool:
        """Test validity of the ``response`` and given ``headers``. Returns True if all tests pass, False otherwise"""
        if not response:
            return False

        self.logger.debug("Begin testing auth response...")

        result = self._test_response(response=response)
        if result:
            result = self._test_expiry(response=response)
        if result:
            try:
                headers = response.headers
            except AuthoriserError:
                headers = None
            result = await self._test_token(headers)

        return result

    def _test_response(self, response: ImmutableJSON) -> bool:
        result = "error" not in response
        self.logger.debug(f"Auth response contains no error test: {result}")
        return result

    def _test_expiry(self, response: ImmutableJSON) -> bool:
        if all(key not in response for key in ("expires_at", "expires_in")) or self.max_expiry <= 0:
            return True

        if "expires_at" in response:
            result = datetime.now().timestamp() + self.max_expiry < response["expires_at"]
        else:
            result = self.max_expiry < response["expires_in"]

        self.logger.debug(f"Token expiry time test: {result}")
        return result

    async def _test_token(self, headers: ImmutableHeaders | None) -> bool:
        if self.request is None or self.response_test is None:
            return True

        with self.request.enrich_parameters("headers", headers):
            async with ClientSession() as session:
                async with self.request(session=session) as response:
                    result = await self.response_test(response)

        self.logger.debug(f"Validate token test: {result}")
        return result if result is not None else False


class SocketHandler:
    """
    :param port: The port to open on the localhost for this socket.
    :param timeout: The time in seconds to keep the socket listening for a request.
    """

    __slots__ = ("port", "timeout", "_socket")

    def __init__(self, port: int = 8080, timeout: int = 120):
        #: The port to open on the localhost for this socket
        self.port = port
        #: The time in seconds to keep the socket listening for a request.
        self.timeout = timeout

        self._socket: socket.socket | None = None

    def __enter__(self) -> socket.socket:
        """Set up socket to listen for the callback"""
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self._socket.bind(("localhost", self.port))
        self._socket.settimeout(self.timeout)
        self._socket.listen(1)
        return self._socket

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._socket.close()
