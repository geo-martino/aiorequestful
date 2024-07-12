"""
Implements OAuth2 authoriser flows.

See specification for more info: https://auth0.com/docs/authenticate/protocols/oauth
"""
import base64
import hashlib
import logging
import secrets
import sys
import uuid
from abc import ABCMeta
from collections.abc import Awaitable
from http import HTTPMethod
from typing import Any, Self
from urllib.parse import unquote
from webbrowser import open as webopen

from aiohttp import ClientSession
from yarl import URL

from aiorequestful._utils import get_iterator
from aiorequestful.auth.base import Authoriser, _DEFAULT_SERVICE_NAME
from aiorequestful.auth.exception import AuthoriserError
from aiorequestful.auth.utils import AuthRequest, AuthResponse, AuthTester, SocketHandler
from aiorequestful.types import URLInput, UnitIterable, Headers


class OAuth2Authoriser(Authoriser, metaclass=ABCMeta):
    """Abstract implementation of an :py:class:`.Authoriser` for OAuth2 authorisation flows."""

    __slots__ = ("token_request", "response", "tester")

    @property
    def is_token_valid(self) -> Awaitable[bool]:
        """Check if the currently loaded token is valid"""
        return self.tester(response=self.response)

    def __init__(
            self,
            token_request: AuthRequest,
            service_name: str = _DEFAULT_SERVICE_NAME,
            response_handler: AuthResponse = None,
            response_tester: AuthTester = None,
    ):
        super().__init__(service_name=service_name)

        #: Request to exchange the authorisation code for an access token
        self.token_request = token_request

        #: Handles saving and loading token request responses and generates headers from a token request
        self.response = response_handler if response_handler is not None else AuthResponse()
        #: Tests the response given from the token request to ensure the token is valid
        self.tester = response_tester if response_tester is not None else AuthTester()

    @staticmethod
    def _encode_client_credentials_as_headers(client_id: str, client_secret: str) -> Headers:
        credentials_encoded = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
        return {
            "Authorization": f"Basic {credentials_encoded}",
        }

    async def _request_token(self, session: ClientSession, request: AuthRequest, params: dict[str, Any] = None) -> None:
        with request.enrich_parameters("params", params if params else {}):
            async with request(session=session) as r:
                self.response.replace(await r.json())

        self.response.enrich(refresh_token=params.get("refresh_token"))

        sanitised_response = self.response.sanitised
        kind = "generated" if not params.get("grant_type") == "refresh_token" else "refreshed"
        self.logger.debug(f"Auth response {kind}: {sanitised_response}")


class ClientCredentialsFlow(OAuth2Authoriser):
    """
    Authorises using OAuth2 specification following the 'Client Credentials' flow specification.

    See more: https://auth0.com/docs/get-started/authentication-and-authorization-flow/client-credentials-flow
    """

    __slots__ = ()

    @classmethod
    def create(
            cls,
            token_request_url: URLInput,
            client_id: str,
            client_secret: str,
            service_name: str = _DEFAULT_SERVICE_NAME,
    ) -> Self:
        """
        Initialises a basic object, generating core request objects from given arguments.
        Sets requests to send the credentials as parameters for each required request.

        :param service_name: The service name for which to authorise.
        :param token_request_url: The URL to call when requesting a new token.
        :param client_id: The client ID.
        :param client_secret: The client secret.
        :return: The initialised object.
        """
        token_request = AuthRequest(
            method=HTTPMethod.POST,
            url=URL(token_request_url),
            params={
                "client_id": client_id,
                "client_secret": client_secret,
            }
        )

        return ClientCredentialsFlow(
            service_name=service_name,
            token_request=token_request,
        )

    @classmethod
    def create_with_encoded_credentials(
            cls,
            token_request_url: URLInput,
            client_id: str,
            client_secret: str,
            service_name: str = _DEFAULT_SERVICE_NAME,
    ) -> Self:
        """
        Initialises a basic object, generating core request objects from given arguments.
        Encodes the client credentials in base64 format and sets requests to send the encoded credentials
        in the headers of each required request.

        :param service_name: The service name for which to authorise.
        :param token_request_url: The URL to call when requesting a new token.
        :param client_id: The client ID.
        :param client_secret: The client secret.
        :return: The initialised object.
        """
        obj = cls.create(
            token_request_url=token_request_url,
            client_id=client_id,
            client_secret="",  # avoid accidentally leaking client secret
            service_name=service_name,
        )

        credentials_headers = cls._encode_client_credentials_as_headers(
            client_id=client_id, client_secret=client_secret
        )

        if hasattr(obj.token_request, "params"):
            obj.token_request.params.pop("client_id", None)
            obj.token_request.params.pop("client_secret", None)
        obj.token_request.headers = credentials_headers

        return obj

    async def authorise(self):
        if not self.response:
            self.response.load_response_from_file()
        loaded = bool(self.response)

        valid = await self.is_token_valid

        if not valid:
            if loaded:
                log = "Saved access token not found"
            else:
                log = "Loaded access token is not valid and and no refresh data found"
            self.logger.debug(f"{log}. Generating new token...")

            params = self._generate_request_token_params()
            async with ClientSession() as session:
                await self._request_token(session=session, request=self.token_request, params=params)

            valid = await self.is_token_valid

        if not self.response:
            raise AuthoriserError("Could not generate or load a token")
        if not valid:
            raise AuthoriserError(f"Auth response is still not valid: {self.response.sanitised}")

        self.logger.debug("Access token is valid. Saving...")
        self.response.save_response_to_file()

        return self.response.headers

    @staticmethod
    def _generate_request_token_params() -> dict[str, Any]:
        return {"grant_type": "client_credentials"}


class AuthorisationCodeFlow(OAuth2Authoriser):
    """
    Authorises using OAuth2 specification following the 'Authorization Code' flow specification.

    See more: https://auth0.com/docs/get-started/authentication-and-authorization-flow/authorization-code-flow

    :param service_name: The service name for which to authorise.
    :param user_request: Request to initiate user authentication and authorisation through an `/authorize` endpoint.
    :param token_request: Request to exchange the authorisation code for an access token.
    :param refresh_request: Request to refresh an access token using the refresh token from the token request response.
    :param redirect_uri: The callback URL to apply to the user request to allow
        for the retrieval of the authorisation code.
        Also sent as a parameter to the token request as part of identity confirmation.
    :param socket_handler: Opens a socket on localhost to listen for a request on the redirect_url.
    :param response_handler: Handles manipulation and storing of the response from a token exchange.
    :param response_tester: Tests the response given from the token request to ensure the token is valid.
    """

    __slots__ = ("user_request", "refresh_request", "redirect_uri", "socket_handler")

    @classmethod
    def create(
            cls,
            user_request_url: URLInput,
            token_request_url: URLInput,
            client_id: str,
            client_secret: str,
            refresh_request_url: URLInput = None,
            scope: UnitIterable[str] = (),
            service_name: str = _DEFAULT_SERVICE_NAME,
    ) -> Self:
        """
        Initialises a basic object, generating core request objects from given arguments.
        Sets requests to send the credentials as parameters for each required request.

        :param service_name: The service name for which to authorise.
        :param user_request_url: The URL to configure for the user to authorise access to the application.
        :param token_request_url: The URL to call when requesting a new token.
        :param refresh_request_url: The URL to call when refreshing a token.
        :param client_id: The client ID.
        :param client_secret: The client secret.
        :param scope: The scope/s to request access for from the user during user authorisation.
        :return: The initialised object.
        """
        user_request = AuthRequest(
            method=HTTPMethod.POST,
            url=URL(user_request_url),
            params={
                "client_id": client_id,
                "scope": " ".join(get_iterator(scope))
            }
        )
        token_request = AuthRequest(
            method=HTTPMethod.POST,
            url=URL(token_request_url),
            params={
                "client_id": client_id,
                "client_secret": client_secret,
            }
        )
        refresh_request = None if not refresh_request_url else AuthRequest(
            method=HTTPMethod.POST,
            url=URL(refresh_request_url),
            params={
                "client_id": client_id,
            }
        )

        return AuthorisationCodeFlow(
            service_name=service_name,
            user_request=user_request,
            token_request=token_request,
            refresh_request=refresh_request
        )

    @classmethod
    def create_with_encoded_credentials(
            cls,
            user_request_url: URLInput,
            token_request_url: URLInput,
            client_id: str,
            client_secret: str,
            refresh_request_url: URLInput = None,
            scope: UnitIterable[str] = (),
            service_name: str = _DEFAULT_SERVICE_NAME,
    ) -> Self:
        """
        Initialises a basic object, generating core request objects from given arguments.
        Encodes the client credentials in base64 format and sets requests to send the encoded credentials
        in the headers of each required request.

        :param service_name: The service name for which to authorise.
        :param user_request_url: The URL to configure for the user to authorise access to the application.
        :param token_request_url: The URL to call when requesting a new token.
        :param refresh_request_url: The URL to call when refreshing a token.
        :param client_id: The client ID.
        :param client_secret: The client secret.
        :param scope: The scope/s to request access for from the user during user authorisation.
        :return: The initialised object.
        """
        obj = cls.create(
            service_name=service_name,
            user_request_url=user_request_url,
            token_request_url=token_request_url,
            refresh_request_url=refresh_request_url,
            client_id=client_id,
            client_secret="",
            scope=scope,
        )

        credentials_headers = cls._encode_client_credentials_as_headers(
            client_id=client_id, client_secret=client_secret
        )

        if hasattr(obj.token_request, "params"):
            obj.token_request.params.pop("client_id", None)
            obj.token_request.params.pop("client_secret", None)
        obj.token_request.headers = credentials_headers

        if obj.refresh_request:
            if hasattr(obj.refresh_request, "params"):
                obj.refresh_request.params.pop("client_id", None)
            obj.refresh_request.headers = credentials_headers

        return obj

    def __init__(
            self,
            user_request: AuthRequest,
            token_request: AuthRequest,
            refresh_request: AuthRequest | None = None,
            service_name: str = _DEFAULT_SERVICE_NAME,
            socket_handler: SocketHandler = None,
            redirect_uri: URLInput = None,
            response_handler: AuthResponse = None,
            response_tester: AuthTester = None,
    ):
        super().__init__(
            service_name=service_name,
            token_request=token_request,
            response_handler=response_handler,
            response_tester=response_tester
        )

        #: Request to initiate user authentication and authorisation through an `/authorize` endpoint
        self.user_request = user_request
        #: Request to refresh an access token using the refresh token from the token request response
        self.refresh_request = refresh_request

        if redirect_uri is None:
            redirect_uri = URL.build(scheme="http", host="localhost", port=8080)
        #: The callback URL to apply to the user request to allow for the retrieval of the authorisation code
        self.redirect_uri = redirect_uri

        if socket_handler is None:
            socket_handler = SocketHandler(port=self.redirect_uri.port)
        #: Opens a socket on localhost to listen for a request on the redirect_url
        self.socket_handler = socket_handler

    async def authorise(self):
        if not self.response:
            self.response.load_response_from_file()
        loaded = bool(self.response)

        if not loaded:
            self.logger.debug("Saved access token not found. Generating new token...")
            async with ClientSession() as session:
                code = await self._authorise_user(session=session)
                params = self._generate_request_token_params(code=code)
                await self._request_token(session=session, request=self.token_request, params=params)

        valid = await self.is_token_valid

        if not valid and loaded:
            valid = await self._handle_invalid_loaded_response()

        if not self.response:
            raise AuthoriserError("Could not generate or load a token")
        if not valid:
            sanitised_response = self.response.sanitised
            raise AuthoriserError(f"Auth response is still not valid: {sanitised_response}")

        self.logger.debug("Access token is valid. Saving...")
        self.response.save_response_to_file()

        return self.response.headers

    async def _handle_invalid_loaded_response(self) -> bool:
        valid = False
        refreshed = False

        async with ClientSession() as session:
            if self.refresh_request and "refresh_token" in self.response:
                self.logger.debug(
                    "Loaded access token is not valid and refresh data found. Refreshing token and testing..."
                )

                params = self._generate_refresh_token_params(refresh_token=self.response["refresh_token"])
                await self._request_token(session=session, request=self.refresh_request, params=params)

                valid = await self.is_token_valid
                refreshed = True

            if not valid:
                if refreshed:
                    log = "Refreshed access token is still not valid"
                else:
                    log = "Loaded access token is not valid and and no refresh data found"
                self.logger.debug(f"{log}. Generating new token...")

                code = await self._authorise_user(session=session)
                params = self._generate_request_token_params(code=code)
                await self._request_token(session=session, request=self.token_request, params=params)

                valid = await self.is_token_valid

        return valid

    def _display_message(self, message: str, level: int = logging.INFO) -> None:
        """Log a message and ensure it is displayed to the user no matter the logger configuration."""
        self.logger.log(level=level, msg=message)

        # return if message was logged to stdout
        for handler in self.logger.handlers + list(logging.getHandlerNames()):
            if isinstance(handler, str):
                handler = logging.getHandlerByName(handler)
            if isinstance(handler, logging.StreamHandler) and handler.stream == sys.stdout:
                return

        print(message)

    def _generate_authorise_user_params(self, state: uuid.UUID) -> dict[str, Any]:
        return {"response_type": "code", "redirect_uri": str(self.redirect_uri), "state": str(state)}

    async def _authorise_user(self, session: ClientSession) -> str:
        self.logger.debug("Authorising user privilege access...")

        state = uuid.uuid4()
        params = self._generate_authorise_user_params(state=state)

        with self.socket_handler as listener, self.user_request.enrich_parameters("params", params):
            self._display_message(
                f"\33[1mOpening {self.service_name} in your browser. "
                f"Log in to {self.service_name}, authorise, and return here after \33[0m"
            )
            self._display_message(f"\33[1mWaiting for code, timeout in {listener.timeout} seconds... \33[0m")

            # open authorise webpage and wait for the redirect
            async with self.user_request(session=session) as r:
                webopen(str(r.url))
            request, _ = listener.accept()

            request.send("Code received! You may now close this window".encode("utf-8"))

        self._display_message("\33[92;1mCode received!\33[0m")

        callback_url = URL(
            next(line for line in request.recv(8196).decode().split('\n') if line.startswith("GET"))
        )

        try:
            callback_state = uuid.UUID(unquote(callback_url.query["state"]))
        except ValueError:
            raise AuthoriserError("Returned state is not a valid UUID")

        if callback_state != state:
            raise AuthoriserError("Invalid state returned")

        return unquote(callback_url.query["code"])

    def _generate_request_token_params(self, code: str) -> dict[str, Any]:
        return {"grant_type": "authorization_code", "code": code, "redirect_uri": str(self.redirect_uri)}

    @staticmethod
    def _generate_refresh_token_params(refresh_token: str) -> dict[str, Any]:
        return {"grant_type": "refresh_token", "refresh_token": refresh_token}


class AuthorisationCodePKCEFlow(AuthorisationCodeFlow):
    """
    Authorises using OAuth2 specification following the 'Authorization Code with PKCE' flow specification.

    See more: https://auth0.com/docs/get-started/authentication-and-authorization-flow/authorization-code-flow-with-pkce

    :param service_name: The service name for which to authorise.
    :param user_request: Request to initiate user authentication and authorisation through an `/authorize` endpoint.
    :param token_request: Request to exchange the authorisation code for an access token.
    :param refresh_request: Request to refresh an access token using the refresh token from the token request response.
    :param redirect_uri: The callback URL to apply to the user request to allow
        for the retrieval of the authorisation code.
        Also sent as a parameter to the token request as part of identity confirmation.
    :param socket_handler: Opens a socket on localhost to listen for a request on the redirect_url.
    :param response_handler: Handles manipulation and storing of the response from a token exchange.
    :param response_tester: Tests the response given from the token request to ensure the token is valid.
    """

    __slots__ = ("code_verifier",)

    @classmethod
    def create(
            cls,
            user_request_url: URLInput,
            token_request_url: URLInput,
            client_id: str,
            refresh_request_url: URLInput = None,
            scope: UnitIterable[str] = (),
            service_name: str = _DEFAULT_SERVICE_NAME,
            **__
    ) -> Self:
        """
        Initialises a basic object, generating core request objects from given arguments.

        :param service_name: The service name for which to authorise.
        :param user_request_url: The URL to configure for the user to authorise access to the application.
        :param token_request_url: The URL to call when requesting a new token.
        :param refresh_request_url: The URL to call when refreshing a token.
        :param client_id: The client ID.
        :param scope: The scope/s to request access for from the user during user authorisation.
        :return: The initialised object.
        """
        user_request = AuthRequest(
            method=HTTPMethod.POST,
            url=URL(user_request_url),
            params={
                "client_id": client_id,
                "scope": " ".join(get_iterator(scope)),
            }
        )
        token_request = AuthRequest(
            method=HTTPMethod.POST,
            url=URL(token_request_url),
            params={
                "client_id": client_id,
            }
        )
        refresh_request = None if not refresh_request_url else AuthRequest(
            method=HTTPMethod.POST,
            url=URL(refresh_request_url),
            params={
                "client_id": client_id,
            }
        )

        return AuthorisationCodePKCEFlow(
            service_name=service_name,
            user_request=user_request,
            token_request=token_request,
            refresh_request=refresh_request
        )

    def __init__(
            self,
            user_request: AuthRequest,
            token_request: AuthRequest,
            refresh_request: AuthRequest | None = None,
            service_name: str = _DEFAULT_SERVICE_NAME,
            socket_handler: SocketHandler = None,
            redirect_uri: URLInput = None,
            response_handler: AuthResponse = None,
            response_tester: AuthTester = None,
            pkce_code_length: int = 128,
    ):
        if not 43 <= pkce_code_length <= 128:
            raise AuthoriserError("PKCE code length must be between 43 and 128 inclusive")
        self.code_verifier = secrets.token_urlsafe(96)[:pkce_code_length]

        super().__init__(
            service_name=service_name,
            user_request=user_request,
            token_request=token_request,
            refresh_request=refresh_request,
            socket_handler=socket_handler,
            redirect_uri=redirect_uri,
            response_handler=response_handler,
            response_tester=response_tester,
        )

    def _generate_authorise_user_params(self, state: uuid.UUID) -> dict[str, Any]:
        code_hashed = hashlib.sha256(self.code_verifier.encode("ascii")).digest()
        code_encoded = base64.urlsafe_b64encode(code_hashed)
        code_challenge = code_encoded.decode("ascii")[:-1]

        return {
            "response_type": "code",
            "redirect_uri": str(self.redirect_uri),
            "state": str(state),
            "code_challenge_method": "S256",
            "code_challenge": code_challenge,
        }

    def _generate_request_token_params(self, code: str) -> dict[str, Any]:
        return {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": str(self.redirect_uri),
            "code_verifier": self.code_verifier
        }


OAUTH2_CLASSES: frozenset[type[OAuth2Authoriser]] = frozenset({
    ClientCredentialsFlow, AuthorisationCodeFlow, AuthorisationCodePKCEFlow,
})
