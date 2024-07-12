"""
Implementations which handle various status codes.

Some operations include:
 * Re-authorising when a 'Not Authorised' status is returned.
 * Waiting until rate limit time has expired when a 'Too Many Requests' status is returned.
"""
import asyncio
import logging
from abc import ABC, abstractmethod
from collections.abc import Awaitable
from datetime import datetime, timedelta
from http import HTTPStatus
from typing import NoReturn

from aiohttp import ClientResponse, ClientSession

from aiorequestful.auth import Authoriser
from aiorequestful.response.exception import ResponseError, StatusHandlerError
from aiorequestful.timer import Timer


class StatusHandler(ABC):
    """
    Handles a response that matches the status conditions of this handler
    according to its status, payload, headers, etc.
    """

    __slots__ = ("logger",)

    @property
    @abstractmethod
    def status_codes(self) -> list[int]:
        """The response status codes this handler can handle."""
        raise NotImplementedError

    def __init__(self):
        #: The :py:class:`logging.Logger` for this  object
        self.logger: logging.Logger = logging.getLogger(__name__)

    def match(self, response: ClientResponse, fail_on_error: bool = False) -> bool:
        """
        Check if this handler settings match the given response.

        :param response: The response to match.
        :param fail_on_error: Raise an exception if the response does not match this handler.
        :raise StatusHandlerError: If match fails and `fail_on_error` is True.
        """
        match = response.status in self.status_codes

        if not match and fail_on_error:
            raise StatusHandlerError(
                "Response status does not match this handler | "
                f"Response={response.status} | Valid={",".join(map(str, self.status_codes))}"
            )
        return match

    def _log(self, response: ClientResponse, message: str = ""):
        status = HTTPStatus(response.status)
        log = [f"Status: {response.status} ({status.phrase}) - {status.description}"]
        if message:
            log.append(message)

        self.logger.debug(" | ".join(log))

    @abstractmethod
    async def handle(self, response: ClientResponse, *_, **__) -> bool:
        """
        Handle the response based on its status, payload response etc.

        :param response: The response to handle.
        :return: True if the response was handled, False if it was not.
        """
        raise NotImplementedError

    def __call__(self, response: ClientResponse, *args, **kwargs) -> Awaitable[bool]:
        return self.handle(response, *args, **kwargs)


class ClientErrorStatusHandler(StatusHandler):
    """Handles status codes which cannot be handled, raising an error."""

    __slots__ = ()

    @property
    def status_codes(self) -> list[int]:
        return [status.value for status in HTTPStatus if 400 <= status.value < 500]

    async def handle(self, response: ClientResponse, *_, **__) -> NoReturn:
        self.match(response=response, fail_on_error=True)

        self._log(response=response, message="Bad response received and cannot handle or continue processing.")
        raise ResponseError(response=response)


class UnauthorisedStatusHandler(StatusHandler):
    """Handles unauthorised response status codes by re-authorising credentials through an :py:class:`Authoriser`."""

    __slots__ = ()

    @property
    def status_codes(self) -> list[int]:
        return [401]

    async def handle(
            self,
            response: ClientResponse,
            authoriser: Authoriser | None = None,
            session: ClientSession | None = None,
            *_,
            **__,
    ) -> bool:
        self.match(response=response, fail_on_error=True)
        if authoriser is None or session is None:
            return False

        self._log(response=response, message="Re-authorising...")
        headers = await authoriser
        session.headers.update(headers)
        return True


class RateLimitStatusHandler(StatusHandler):
    """Handles rate limits by increasing a timer value for every response that returns a rate limit status."""

    __slots__ = ("_wait_logged",)

    @property
    def status_codes(self) -> list[int]:
        return [429]

    def __init__(self):
        super().__init__()
        self._wait_logged = False

    async def handle(
            self,
            response: ClientResponse,
            wait_timer: Timer | None = None,
            retry_timer: Timer | None = None,
            *_,
            **__
    ) -> bool:
        self.match(response=response, fail_on_error=True)
        if wait_timer is not None:
            self._increase_wait(response=response, wait_timer=wait_timer)

        if "retry-after" not in response.headers:
            return False

        wait_seconds = int(response.headers["retry-after"])
        wait_dt_str = (datetime.now() + timedelta(seconds=wait_seconds)).strftime("%Y-%m-%d %H:%M:%S")

        if retry_timer is not None and wait_seconds > retry_timer.total:  # exception if too long
            raise ResponseError(
                "Rate limit exceeded and wait time is greater than remaining timeout "
                f"of {retry_timer.total_remaining:.2f} seconds. Retry again at {wait_dt_str}"
            )

        if not self._wait_logged:
            self.logger.warning(f"\33[93mRate limit exceeded. Retrying again at {wait_dt_str}\33[0m")
            self._wait_logged = True

        await asyncio.sleep(wait_seconds)
        self._wait_logged = False

        return True

    def _increase_wait(self, response: ClientResponse, wait_timer: Timer):
        if wait_timer.increase():
            self._log(
                response=response,
                message=f"Increasing wait time between requests to {float(wait_timer):.2f}s"
            )
        else:
            self._log(
                response=response,
                message=f"Cannot increase wait time. Already at maximum of {float(wait_timer):.2f}s"
            )
