import re
import socket
import uuid
from abc import ABC, abstractmethod
from http import HTTPMethod
from pathlib import Path
from random import randrange, choice
from typing import Any
from unittest.mock import AsyncMock
from urllib.parse import unquote

import pytest
from aiohttp import ClientSession
from aioresponses import aioresponses, CallbackResult
from pytest_mock import MockerFixture
from yarl import URL

from aiorequestful import MODULE_ROOT
from aiorequestful.auth.exception import AuthoriserError
from aiorequestful.auth.oauth2 import OAuth2Authoriser, ClientCredentialsFlow, AuthorisationCodeFlow, \
    AuthorisationCodePKCEFlow
from aiorequestful.auth.utils import AuthRequest, AuthResponse
from aiorequestful.types import JSON
from tests.auth.utils import response_enrich_keys
from tests.utils import path_token


@pytest.fixture
def auth_response() -> JSON:
    return {
        "access_token": "fake access token",
        "token_type": "Bearer",
        "expires_in": 3600,
        "scope": "test-read",
    }


def assert_response(actual: JSON, expected: JSON) -> None:
    assert {k: v for k, v in actual.items() if k not in response_enrich_keys} == expected
    assert "granted_at" in actual
    assert "expires_at" in actual


class OAuth2Tester(ABC):
    @abstractmethod
    def authoriser(self) -> OAuth2Authoriser:
        raise NotImplementedError

    @abstractmethod
    def token_request_params(self, authoriser: OAuth2Authoriser, **__) -> dict[str, Any]:
        raise NotImplementedError

    @pytest.fixture(params=[path_token])
    def response_file_path(self, path: Path) -> Path:
        """Yield the temporary path for the token response JSON file"""
        return path

    @staticmethod
    async def test_request_token(
            authoriser: ClientCredentialsFlow,
            token_request_params: dict[str, Any],
            auth_response: JSON,
            requests_mock: aioresponses
    ):
        def exchange_response_for_token(*_, params: dict[str, str], **__) -> CallbackResult:
            for k, expected in token_request_params.items():
                assert params[k] == expected
            return CallbackResult(payload=auth_response)

        requests_mock.post(re.compile(str(authoriser.token_request.url)), callback=exchange_response_for_token)

        async with ClientSession() as session:
            await authoriser._request_token(
                session, request=authoriser.token_request, payload=token_request_params
            )

        assert_response(authoriser.response._response, auth_response)


class TestClientCredentialsFlow(OAuth2Tester):

    @pytest.fixture
    def authoriser(self) -> ClientCredentialsFlow:
        token_request = AuthRequest(
            method=HTTPMethod.POST,
            url=URL("http://localhost/api/token"),
        )

        return ClientCredentialsFlow(
            service_name="test",
            token_request=token_request,
        )

    @pytest.fixture
    def token_request_params(self, authoriser: ClientCredentialsFlow, **__) -> dict[str, Any]:
        return authoriser._generate_request_token_payload()

    @pytest.fixture
    def mock_request_token(self, authoriser: ClientCredentialsFlow, mocker: MockerFixture) -> AsyncMock:
        def _request_token(*_, **__) -> None:
            authoriser.response._response = {
                authoriser.response.token_key: "request"
            }

        return mocker.patch.object(
            ClientCredentialsFlow,
            attribute="_request_token",
            side_effect=_request_token,
            new_callable=AsyncMock,
        )

    @pytest.fixture
    def mock_tester(self, authoriser: ClientCredentialsFlow, mocker: MockerFixture) -> AsyncMock:
        return mocker.patch.object(
            ClientCredentialsFlow, attribute="tester", side_effect=AsyncMock(return_value=True),
        )

    @pytest.fixture
    def mock_save(self, mocker: MockerFixture) -> AsyncMock:
        return mocker.patch.object(AuthResponse, attribute="save_response_to_file")

    ###########################################################################
    ## Main authorise method
    ###########################################################################
    async def test_authorise_uses_loaded_response(
            self,
            authoriser: ClientCredentialsFlow,
            auth_response: JSON,
            mock_request_token: AsyncMock,
            mock_tester: AsyncMock,
            mock_save: AsyncMock,
    ):
        authoriser.response._response = auth_response
        assert not authoriser.response.file_path

        await authoriser

        mock_request_token.assert_not_called()
        mock_tester.assert_called_once()
        mock_save.assert_called_once()

    async def test_authorise_load_from_file(
            self,
            authoriser: ClientCredentialsFlow,
            response_file_path: Path,
            mock_request_token: AsyncMock,
            mock_tester: AsyncMock,
            mock_save: AsyncMock,
    ):
        assert not authoriser.response._response
        authoriser.response.file_path = response_file_path

        await authoriser

        mock_request_token.assert_not_called()
        mock_tester.assert_called_once()
        mock_save.assert_called_once()

    async def test_authorise_loaded_response_invalid(
            self,
            authoriser: ClientCredentialsFlow,
            response_file_path: Path,
            auth_response: JSON,
            mock_request_token: AsyncMock,
            mock_save: AsyncMock,
            mocker: MockerFixture,
    ):
        async def tester(response: AuthResponse) -> bool:
            original_token = auth_response[authoriser.response.token_key]
            if response[authoriser.response.token_key] == original_token:
                return False
            return True

        mock_tester = mocker.patch.object(
            authoriser, attribute="tester", side_effect=tester, new_callable=AsyncMock
        )

        assert not authoriser.response._response
        authoriser.response.file_path = response_file_path

        await authoriser

        mock_request_token.assert_called_once()
        assert mock_tester.call_count == 2
        mock_save.assert_called_once()

    async def test_authorise_new_token(
            self,
            authoriser: ClientCredentialsFlow,
            mock_request_token: AsyncMock,
            mocker: MockerFixture,
    ):
        assert not authoriser.response._response
        assert not authoriser.response.file_path

        async def tester(response: AuthResponse) -> bool:
            return bool(response)

        mock_tester = mocker.patch.object(
            authoriser, attribute="tester", side_effect=tester, new_callable=AsyncMock
        )

        await authoriser

        mock_request_token.assert_called_once()
        assert mock_tester.call_count == 2

    async def test_authorise_no_response(
            self,
            authoriser: ClientCredentialsFlow,
            mocker: MockerFixture
    ):
        assert not authoriser.response._response
        assert not authoriser.response.file_path

        mocker.patch.object(ClientCredentialsFlow, attribute="_request_token", return_value={})

        with pytest.raises(AuthoriserError, match="not generate or load"):
            await authoriser

    async def test_authorise_invalid_response(
            self,
            authoriser: ClientCredentialsFlow,
            mock_request_token: AsyncMock,
            mocker: MockerFixture
    ):
        assert not authoriser.response._response
        assert not authoriser.response.file_path

        mocker.patch.object(authoriser, attribute="tester", side_effect=AsyncMock(return_value=False))

        with pytest.raises(AuthoriserError, match="still not valid"):
            await authoriser


class TestAuthorisationCodeFlow(OAuth2Tester):

    @pytest.fixture
    def authoriser(self) -> AuthorisationCodeFlow:
        user_request = AuthRequest(
            method=HTTPMethod.POST,
            url=URL("http://localhost/authorize"),
        )
        token_request = AuthRequest(
            method=HTTPMethod.POST,
            url=URL("http://localhost/api/token"),
        )
        refresh_request = AuthRequest(
            method=HTTPMethod.POST,
            url=URL("http://localhost/api/token/refresh"),
        )

        return AuthorisationCodeFlow(
            service_name="test",
            user_request=user_request,
            token_request=token_request,
            refresh_request=refresh_request,
            redirect_uri=URL("http://localhost/redirect"),
        )

    # noinspection PyMethodOverriding
    @pytest.fixture
    def token_request_params(self, authoriser: AuthorisationCodeFlow, user_auth_code: str, **__) -> dict[str, Any]:
        return authoriser._generate_request_token_payload(code=user_auth_code)

    @pytest.fixture
    def user_auth_code(
            self, authoriser: AuthorisationCodeFlow, mocker: MockerFixture, requests_mock: aioresponses
    ) -> str:
        socket_listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        mocker.patch.object(socket.socket, attribute="accept", return_value=(socket_listener, None))
        mocker.patch.object(socket.socket, attribute="send")
        mocker.patch.object(socket.socket, attribute="close")

        requests_mock.add(
            method=authoriser.user_request.method.name,
            url=re.compile(str(authoriser.user_request.url)),
            repeat=True,
        )

        return "test-code"

    @pytest.fixture
    def mock_user_auth(self, mocker: MockerFixture) -> AsyncMock:
        return mocker.patch.object(
            AuthorisationCodeFlow, attribute="_authorise_user", side_effect=AsyncMock(return_value="test-code")
        )

    @pytest.fixture
    def mock_request_token(self, authoriser: ClientCredentialsFlow, mocker: MockerFixture) -> AsyncMock:
        def _request_token(*_, **__) -> JSON:
            authoriser.response._response = {
                authoriser.response.token_key: "request"
            }
            return authoriser.response._response

        return mocker.patch.object(
            AuthorisationCodeFlow,
            attribute="_request_token",
            side_effect=_request_token,
            new_callable=AsyncMock,
        )

    @pytest.fixture
    def mock_tester(self, authoriser: AuthorisationCodeFlow, mocker: MockerFixture) -> AsyncMock:
        return mocker.patch.object(
            AuthorisationCodeFlow, attribute="tester", side_effect=AsyncMock(return_value=True),
        )

    @pytest.fixture
    def mock_save(self, mocker: MockerFixture) -> AsyncMock:
        return mocker.patch.object(AuthResponse, attribute="save_response_to_file")

    ###########################################################################
    ## User authorisation
    ###########################################################################
    async def test_authorise_user_successful(
            self, authoriser: AuthorisationCodeFlow, user_auth_code: str, mocker: MockerFixture
    ):
        def handle_user_request_successfully(url: str):
            """Check the URL given to the webopen call and patch socket response"""
            url = URL(url)

            assert str(url.with_query(None)) == str(authoriser.user_request.url)
            assert unquote(url.query["response_type"]) == "code"
            assert unquote(url.query["redirect_uri"]) == str(authoriser.redirect_uri)

            response = f"GET /?code={user_auth_code}&state={URL(url).query["state"]}"
            mocker.patch.object(socket.socket, attribute="recv", return_value=response.encode("utf-8"))

        authoriser.socket_handler.port = 8000
        mocker.patch(f"{MODULE_ROOT}.auth.oauth2.webopen", new=handle_user_request_successfully)

        async with ClientSession() as session:
            assert await authoriser._authorise_user(session) == user_auth_code

    async def test_authorise_user_with_bad_state_response(
            self, authoriser: AuthorisationCodeFlow, user_auth_code: str, mocker: MockerFixture
    ):
        def handle_user_request_with_bad_state(_: str):
            response = f"GET /?code={user_auth_code}&state={uuid.uuid4()}"
            mocker.patch.object(socket.socket, attribute="recv", return_value=response.encode("utf-8"))

        authoriser.socket_handler.port = 8001
        mocker.patch(f"{MODULE_ROOT}.auth.oauth2.webopen", new=handle_user_request_with_bad_state)

        with pytest.raises(AuthoriserError):
            async with ClientSession() as session:
                await authoriser._authorise_user(session)

    ###########################################################################
    ## Request/refresh token
    ###########################################################################
    async def test_refresh_token(
            self, authoriser: AuthorisationCodeFlow, auth_response: JSON, requests_mock: aioresponses
    ):
        def exchange_response_for_token(*_, params: dict[str, str], **__) -> CallbackResult:
            assert params["grant_type"] == "refresh_token"
            assert params["refresh_token"] == refresh_token

            return CallbackResult(payload=auth_response)

        refresh_token = "test-token"
        requests_mock.post(re.compile(str(authoriser.token_request.url)), callback=exchange_response_for_token)

        request_params = authoriser._generate_refresh_token_payload(refresh_token=refresh_token)
        async with ClientSession() as session:
            await authoriser._request_token(session, request=authoriser.refresh_request, payload=request_params)

        assert_response(authoriser.response._response, auth_response)
        assert "refresh_token" not in getattr(authoriser.token_request, "params", {})

    ###########################################################################
    ## Handle invalid loaded response
    ###########################################################################
    async def test_handle_invalid_loaded_response_with_no_refresh_token(
            self,
            authoriser: AuthorisationCodeFlow,
            auth_response: JSON,
            mock_user_auth: AsyncMock,
            mock_request_token: AsyncMock,
            mock_tester: AsyncMock,
    ):
        assert "refresh_token" not in auth_response
        authoriser.response.replace(auth_response)
        valid = await authoriser._handle_invalid_loaded_response()

        mock_user_auth.assert_called_once()
        mock_request_token.assert_called_once()
        mock_tester.assert_called_once()

        assert authoriser.response._response == await mock_request_token()
        assert valid

    async def test_handle_invalid_loaded_response_with_no_refresh_request(
            self,
            authoriser: AuthorisationCodeFlow,
            auth_response: JSON,
            mock_user_auth: AsyncMock,
            mock_request_token: AsyncMock,
            mock_tester: AsyncMock,
    ):
        authoriser.refresh_request = None
        authoriser.response["refresh_token"] = "token"
        valid = await authoriser._handle_invalid_loaded_response()

        mock_user_auth.assert_called_once()
        mock_request_token.assert_called_once()
        mock_tester.assert_called_once()

        assert authoriser.response._response == await mock_request_token()
        assert valid

    async def test_handle_invalid_loaded_response_with_valid_refresh(
            self,
            authoriser: AuthorisationCodeFlow,
            auth_response: JSON,
            mock_user_auth: AsyncMock,
            mock_request_token: AsyncMock,
            mock_tester: AsyncMock,
    ):
        authoriser.response["refresh_token"] = "token"
        valid = await authoriser._handle_invalid_loaded_response()

        mock_user_auth.assert_not_called()
        mock_request_token.assert_called_once()
        mock_tester.assert_called_once()

        assert authoriser.response._response == await mock_request_token()
        assert valid

    async def test_handle_invalid_loaded_response_with_invalid_refresh(
            self,
            authoriser: AuthorisationCodeFlow,
            auth_response: JSON,
            mock_user_auth: AsyncMock,
            mocker: MockerFixture,
    ):
        async def request_token(payload: dict[str, Any], **__) -> JSON:
            if payload["grant_type"] == "refresh_token":
                response = {authoriser.response.token_key: "refresh"}
            else:
                response = {authoriser.response.token_key: "request"}

            authoriser.response._response = response
            return response

        async def tester(response: AuthResponse) -> bool:
            if response["access_token"] == "refresh":
                return False
            return True

        mock_request_token = mocker.patch.object(
            AuthorisationCodeFlow,
            attribute="_request_token",
            side_effect=request_token,
            new_callable=AsyncMock
        )
        mocker.patch.object(
            AuthorisationCodeFlow, attribute="tester", side_effect=tester, new_callable=AsyncMock
        )

        # with refresh token and good response
        authoriser.response["refresh_token"] = "token"
        valid = await authoriser._handle_invalid_loaded_response()

        mock_user_auth.assert_called_once()
        assert mock_request_token.call_count == 2

        assert authoriser.response._response == await request_token(payload={"grant_type": "request"})
        assert valid

    ###########################################################################
    ## Main authorise method
    ###########################################################################
    async def test_authorise_uses_loaded_response(
            self,
            authoriser: AuthorisationCodeFlow,
            auth_response: JSON,
            mock_user_auth: AsyncMock,
            mock_request_token: AsyncMock,
            mock_tester: AsyncMock,
            mock_save: AsyncMock,
    ):
        authoriser.response._response = auth_response
        assert not authoriser.response.file_path

        await authoriser

        mock_user_auth.assert_not_called()
        mock_request_token.assert_not_called()
        mock_tester.assert_called_once()
        mock_save.assert_called_once()

    async def test_authorise_load_from_file(
            self,
            authoriser: AuthorisationCodeFlow,
            response_file_path: Path,
            mock_user_auth: AsyncMock,
            mock_request_token: AsyncMock,
            mock_tester: AsyncMock,
            mock_save: AsyncMock,
    ):
        assert not authoriser.response._response
        authoriser.response.file_path = response_file_path

        await authoriser

        mock_user_auth.assert_not_called()
        mock_request_token.assert_not_called()
        mock_tester.assert_called_once()
        mock_save.assert_called_once()

    async def test_authorise_loaded_response_invalid(
            self,
            authoriser: AuthorisationCodeFlow,
            response_file_path: Path,
            auth_response: JSON,
            mock_user_auth: AsyncMock,
            mock_request_token: AsyncMock,
            mock_save: AsyncMock,
            mocker: MockerFixture,
    ):
        async def tester(response: AuthResponse) -> bool:
            original_token = auth_response[authoriser.response.token_key]
            if response[authoriser.response.token_key] == original_token:
                return False
            return True

        mock_tester = mocker.patch.object(
            AuthorisationCodeFlow, attribute="tester", side_effect=tester, new_callable=AsyncMock
        )
        mock_invalid_handler = mocker.patch.object(
            AuthorisationCodeFlow, attribute="_handle_invalid_loaded_response", return_value=(auth_response, True)
        )

        assert not authoriser.response._response
        authoriser.response.file_path = response_file_path

        await authoriser

        mock_user_auth.assert_not_called()
        mock_request_token.assert_not_called()
        mock_invalid_handler.assert_called_once()
        mock_tester.assert_called_once()
        mock_save.assert_called_once()

    async def test_authorise_new_token(
            self,
            authoriser: AuthorisationCodeFlow,
            mock_user_auth: AsyncMock,
            mock_request_token: AsyncMock,
            mock_tester: AsyncMock,
    ):
        assert not authoriser.response._response
        assert not authoriser.response.file_path

        await authoriser

        mock_user_auth.assert_called_once()
        mock_request_token.assert_called_once()
        mock_tester.assert_called_once()

    async def test_authorise_no_response(
            self,
            authoriser: AuthorisationCodeFlow,
            mock_user_auth: AsyncMock,
            mocker: MockerFixture
    ):
        assert not authoriser.response._response
        assert not authoriser.response.file_path

        mocker.patch.object(AuthorisationCodeFlow, attribute="_request_token", return_value={})

        with pytest.raises(AuthoriserError, match="not generate or load"):
            await authoriser

    async def test_authorise_invalid_response(
            self,
            authoriser: AuthorisationCodeFlow,
            mock_user_auth: AsyncMock,
            mock_request_token: AsyncMock,
            mocker: MockerFixture
    ):
        assert not authoriser.response._response
        assert not authoriser.response.file_path

        mocker.patch.object(
            AuthorisationCodeFlow, attribute="tester", side_effect=AsyncMock(return_value=False)
        )

        with pytest.raises(AuthoriserError, match="still not valid"):
            await authoriser


class TestAuthorisationCodePKCEFlow(OAuth2Tester):

    @pytest.fixture
    def authoriser(self) -> AuthorisationCodePKCEFlow:
        user_request = AuthRequest(
            method=HTTPMethod.POST,
            url=URL("http://localhost/authorize"),
        )
        token_request = AuthRequest(
            method=HTTPMethod.POST,
            url=URL("http://localhost/api/token"),
        )
        refresh_request = AuthRequest(
            method=HTTPMethod.POST,
            url=URL("http://localhost/api/token/refresh"),
        )

        return AuthorisationCodePKCEFlow(
            service_name="test",
            user_request=user_request,
            token_request=token_request,
            refresh_request=refresh_request,
            redirect_uri=URL("http://localhost/redirect"),
        )

    @pytest.fixture
    def token_request_params(self, authoriser: AuthorisationCodePKCEFlow, **__) -> dict[str, Any]:
        return authoriser._generate_request_token_payload(code="test-code")

    def test_init_fails(self, authoriser: AuthorisationCodePKCEFlow):
        with pytest.raises(AuthoriserError):
            AuthorisationCodePKCEFlow(
                user_request=authoriser.user_request,
                token_request=authoriser.token_request,
                pkce_code_length=choice([randrange(-10, 42), randrange(129, 200)]),
            )

    def test_generate_authorise_user_params(self, authoriser: AuthorisationCodePKCEFlow):
        params = authoriser._generate_authorise_user_payload(state=uuid.uuid4())
        assert params

    def test_generate_request_token_params(self, authoriser: AuthorisationCodePKCEFlow):
        params = authoriser._generate_request_token_payload(code="test-code")
        assert params
