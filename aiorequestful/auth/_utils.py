import json
import logging
import socket
from contextlib import contextmanager, asynccontextmanager
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import MutableMapping, Any, Literal, Generator, Coroutine, Callable, Awaitable, Unpack

from aiohttp import ClientSession, ClientResponse
from yarl import URL

from aiorequestful.exception import AuthoriserError
from aiorequestful.types import MethodInput, URLInput, Method, Headers, ImmutableHeaders, MutableJSON, ImmutableJSON, \
    JSON, Request


class AuthRequest:
    """
    Request handler for sending authentication and authorisation requests.
    Supply this class with the required arguments for your request.

    :param method: HTTP request method (such as GET, POST, PUT, etc.).
    :param url: The URL of the request.
    :param **kwargs: Any other kwargs required for a successful request.
    """

    def __init__(self, method: MethodInput, url: URLInput, **kwargs: Unpack[Request]):
        self.method = Method.get(method)
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
            self, key: Literal["data", "params", "json"], value: dict[str, Any]
    ) -> Generator[None, None, None]:
        """
        Temporarily append data to the parameters of a request and remove when done.

        :param key: The keyword of the argument to append data to.
        :param value: The value to append.
        """
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
        kwargs = {k: deepcopy(v) for k, v in vars(self).items() if k not in ("method", "url")}
        self._sanitise_kwargs(kwargs)

        async with session.request(method=self.method.name, url=self.url, **kwargs) as response:
            yield response


class AuthResponseHandler:
    """
    Handle saving, loading, enriching, sanitising etc. of responses.
    Also handles token extraction and header generation from token responses.

    Ideally, usage of this class should ensure that the stored response is valid i.e.
    a response should not be stored on this class if it is invalid.

    :param file_path: Path to use for loading and saving a token.
    :param token_prefix_default: Prefix to add to the header value for authorised calls to an endpoint.
    :param additional_headers: Extra headers to add to the final headers to ensure future successful requests.
    """

    @property
    def token(self) -> str:
        """Extract the token from the stored response."""
        if not self.response:
            raise AuthoriserError("Stored response is not available.")

        if self.token_key not in self.response:
            raise AuthoriserError(
                f"Did not find valid token at key: {self.token_key} | {self.sanitise_response()}"
            )
        return str(self.response[self.token_key])

    @property
    def headers(self) -> Headers:
        """Generate headers from the stored response, adding all additional headers as needed."""
        header_key = "Authorization"
        header_prefix = self.response.get("token_type", self.token_prefix_default)

        headers = {header_key: f"{header_prefix} {self.token}"}
        if self.additional_headers:
            headers.update(self.additional_headers)
        return headers

    def __init__(
            self,
            file_path: str | Path = None,
            token_prefix_default: str | None = None,
            additional_headers: ImmutableHeaders = None,
    ):
        #: The :py:class:`logging.Logger` for this  object
        self.logger: logging.Logger = logging.getLogger(__name__)

        self.response: MutableJSON | None = None

        self.file_path: Path | None = Path(file_path).with_suffix(".json") if file_path else None
        self.token_key: str = "access_token"
        self.token_prefix_default: str | None = token_prefix_default

        self.additional_headers = additional_headers

    def sanitise_response(self, response: ImmutableJSON = None) -> JSON:
        """
        Returns a reformatted ``response``, making it safe to log by removing sensitive values at predefined keys.
        If no ``response`` is given, uses the stored response.
        """
        response = response or self.response
        if not response:
            return {}

        def _clean_value(value: Any) -> str:
            value = str(value)
            if len(value) < 5:
                return ""
            return f"{value[:5]}..."

        response_clean = {k: _clean_value(v) if str(k).endswith("_token") else v for k, v in response.items()}
        if self.token_key in response_clean:
            response_clean[self.token_key] = _clean_value(response_clean[self.token_key])

        return response_clean

    def enrich_response(self, response: MutableJSON = None, refresh_token: str = None) -> None:
        """
        Extends the ``response`` by adding granted and expiry time information to it.
        Adds the given ``refresh_token`` to the response if one is not present.
        If no ``response`` is given, uses the stored response.
        """
        response = response or self.response
        if not response:
            return

        # add granted and expiry times to token
        response["granted_at"] = datetime.now().timestamp()
        if "expires_in" in response:
            expires_at = response["granted_at"] + float(response["expires_in"])
            response["expires_at"] = expires_at

        # request usually does return a new refresh token, but add the previous one if not
        if "refresh_token" not in response and refresh_token:
            response["refresh_token"] = refresh_token

    def load_response_from_file(self) -> JSON | None:
        """Load a stored response from given path"""
        if not self.file_path or not self.file_path.exists():
            return

        self.logger.debug("Saved authorisation code response found. Loading...")
        with open(self.file_path, "r") as file:  # load token
            self.response = json.load(file)

        return self.response

    def save_response_to_file(self, response: MutableJSON = None) -> None:
        """
        Save a ``response`` to given path.
        If a ``response`` is given, updates the stored response.
        If no ``response`` is given, saves the stored response.
        """
        self.response = response or self.response
        if not self.file_path or not self.response:
            return

        self.logger.debug(f"Saving authorisation code response: {self.sanitise_response()}")
        with open(self.file_path, "w") as file:
            json.dump(self.response, file, indent=2)


class AuthResponseTester:
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
    def __init__(
            self,
            request: AuthRequest | None = None,
            response_test: Callable[[ClientResponse], Awaitable[bool]] | None = None,
            max_expiry: int = 0,
    ):
        #: The :py:class:`logging.Logger` for this  object
        self.logger: logging.Logger = logging.getLogger(__name__)

        self.request = request
        self.response_test = response_test
        #: The max allowed time in seconds left until the token is due to expire
        self.max_expiry = max_expiry

    def __call__(
            self, response: ImmutableJSON | None = None, headers: ImmutableHeaders | None = None
    ) -> Awaitable[bool]:
        return self.test(response=response, headers=headers)

    async def test(self, response: ImmutableJSON | None = None, headers: ImmutableHeaders | None = None) -> bool:
        """Test validity of the ``response`` and given ``headers``. Returns True if all tests pass, False otherwise"""
        if not response:
            return False

        self.logger.debug("Begin testing auth response...")

        result = self._test_response(response=response)
        if result:
            result = self._test_expiry(response=response)
        if result:
            result = await self._test_token(headers=headers)

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
