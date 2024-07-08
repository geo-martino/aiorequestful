import logging
import sys
import uuid
from urllib.parse import unquote
from webbrowser import open as webopen

from aiohttp import ClientSession
from yarl import URL

from aiorequestful.auth._base import Authoriser
from aiorequestful.auth._utils import AuthRequest, AuthResponseHandler, AuthResponseTester, SocketHandler
from aiorequestful.exception import AuthoriserError
from aiorequestful.types import ImmutableJSON, JSON, URLInput


class OAuth2AuthCode(Authoriser):
    """
    Authorises using OAuth2 specification following the 'Authorization Code' flow.

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

    def __init__(
            self,
            user_request: AuthRequest,
            token_request: AuthRequest,
            refresh_request: AuthRequest | None = None,
            service_name: str = "unknown service",
            socket_handler: SocketHandler = None,
            redirect_uri: URLInput = None,
            response_handler: AuthResponseHandler = None,
            response_tester: AuthResponseTester = None,
    ):
        super().__init__(service_name=service_name)

        #: Request to initiate user authentication and authorisation through an `/authorize` endpoint
        self.user_request = user_request
        #: Request to exchange the authorisation code for an access token
        self.token_request = token_request
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

        #: Handles saving and loading token request responses and generates headers from a token request
        self.response_handler = response_handler if response_handler is not None else AuthResponseHandler()
        #: Tests the response given from the token request to ensure the token is valid
        self.response_tester = response_tester if response_tester is not None else AuthResponseTester()

    async def authorise(self):
        response = self.response_handler.response
        if not response:
            response = self.response_handler.load_response_from_file()
        loaded = response is not None and response.items()

        if not loaded:
            self.logger.debug("Saved access token not found. Generating new token...")
            async with ClientSession() as session:
                code = await self._authorise_user(session=session)
                response = await self._request_token(session=session, code=code)

        valid = await self.response_tester(response=response)

        if not valid and loaded:
            response, valid = await self._handle_invalid_loaded_response(response=response)

        if not response:
            raise AuthoriserError("Could not generate or load a token")
        if not valid:
            sanitised_response = self.response_handler.sanitise_response(response)
            raise AuthoriserError(f"Auth response is still not valid: {sanitised_response}")

        self.logger.debug("Access token is valid. Saving...")
        self.response_handler.save_response_to_file(response=response)

        return self.response_handler.headers

    async def _handle_invalid_loaded_response(self, response: ImmutableJSON) -> tuple[JSON, bool]:
        valid = False
        refreshed = False

        async with ClientSession() as session:
            if self.refresh_request and "refresh_token" in response:
                self.logger.debug(
                    "Loaded access token is not valid and refresh data found. Refreshing token and testing..."
                )

                response = await self._refresh_token(session=session, refresh_token=response["refresh_token"])
                valid = await self.response_tester(response=response)
                refreshed = True

            if not valid:
                if refreshed:
                    log = "Refreshed access token is still not valid"
                else:
                    log = "Loaded access token is not valid and and no refresh data found"
                self.logger.debug(f"{log}. Generating new token...")

                code = await self._authorise_user(session=session)
                response = await self._request_token(session=session, code=code)
                valid = await self.response_tester(response=response)

        return response, valid

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

    async def _authorise_user(self, session: ClientSession) -> str:
        """
        Get user authentication code by authorising through user's browser.

        :param session: The ClientSession to use for the request.
        :return: The authentication code to exchange for an access token.
        """
        self.logger.debug("Authorising user privilege access...")

        state = str(uuid.uuid4())
        params = {"redirect_uri": str(self.redirect_uri), "state": state}

        with self.socket_handler as sckt, self.user_request.enrich_parameters("params", params):
            self._display_message(
                f"\33[1mOpening {self.service_name} in your browser. "
                f"Log in to {self.service_name}, authorise, and return here after \33[0m"
            )
            self._display_message(f"\33[1mWaiting for code, timeout in {sckt.timeout} seconds... \33[0m")

            # open authorise webpage and wait for the redirect
            async with self.user_request(session=session) as r:
                webopen(str(r.url))
            request, _ = sckt.accept()

            request.send("Code received! You may now close this window".encode("utf-8"))

        self._display_message("\33[92;1mCode received!\33[0m")

        callback_url = URL(
            next(line for line in request.recv(8196).decode("utf-8").split('\n') if line.startswith("GET"))
        )
        callback_state = unquote(callback_url.query["state"])
        if callback_state != state:
            raise AuthoriserError("Invalid state returned")

        return unquote(callback_url.query["code"])

    async def _request_token(self, session: ClientSession, code: str) -> JSON:
        """
        Exchange the auth code for an access token and return the response.

        :param session: The ClientSession to use for the request.
        :param code: The code to add to the body parameters of the request.
        :return: The response from the exchange.
        """
        params = {"code": code, "redirect_uri": str(self.redirect_uri)}
        with self.token_request.enrich_parameters("params", params):
            async with self.token_request(session=session) as r:
                response = await r.json()

        self.response_handler.enrich_response(response)

        sanitised_response = self.response_handler.sanitise_response(response)
        self.logger.debug(f"New auth response generated: {sanitised_response}")
        return response

    async def _refresh_token(self, session: ClientSession, refresh_token: str) -> JSON:
        """
        Exchange a refresh token for an access token and return the response.

        :param session: The ClientSession to use for the request.
        :param refresh_token: The refresh token to the body parameters of the request.
        :return: The response from the exchange.
        """
        with self.refresh_request.enrich_parameters("params", {"refresh_token": refresh_token}):
            async with self.refresh_request(session=session) as r:
                response = await r.json()

        self.response_handler.enrich_response(response, refresh_token=refresh_token)

        sanitised_response = self.response_handler.sanitise_response(response)
        self.logger.debug(f"Auth response refreshed: {sanitised_response}")
        return response
