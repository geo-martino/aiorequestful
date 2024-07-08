import re
import socket
from pathlib import Path
from unittest.mock import AsyncMock
from urllib.parse import unquote

import pytest
from aiohttp import ClientSession
from aioresponses import aioresponses, CallbackResult
from pytest_mock import MockerFixture
from yarl import URL

from aiorequestful import MODULE_ROOT
from aiorequestful.auth import AuthRequest
from aiorequestful.auth.oauth2 import OAuth2AuthCode
from aiorequestful.exception import AuthoriserError
from aiorequestful.types import Method, JSON
from tests.auth.utils import response_enrich_keys
from tests.utils import path_token


class TestOAuth2AuthCode:

    @pytest.fixture
    def authoriser(self) -> OAuth2AuthCode:
        user_request = AuthRequest(
            method=Method.POST,
            url=URL("http://localhost/authorize"),
        )
        token_request = AuthRequest(
            method=Method.POST,
            url=URL("http://localhost/api/token"),
        )
        refresh_request = AuthRequest(
            method=Method.POST,
            url=URL("http://localhost/api/token/refresh"),
        )

        return OAuth2AuthCode(
            service_name="test",
            user_request=user_request,
            token_request=token_request,
            refresh_request=refresh_request,
            redirect_uri=URL("http://localhost/redirect"),
        )

    @pytest.fixture
    def auth_response(self, authoriser: OAuth2AuthCode) -> JSON:
        return {
            authoriser.response_handler.token_key: "fake access token",
            "token_type": "Bearer",
            "expires_in": 3600,
            "scope": "test-read",
        }

    @pytest.fixture(params=[path_token])
    def response_file_path(self, path: Path) -> Path:
        """Yield the temporary path for the token response JSON file"""
        return path

    @pytest.fixture
    def user_auth_code(self, authoriser: OAuth2AuthCode, mocker: MockerFixture, requests_mock: aioresponses) -> str:
        socket_listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        mocker.patch.object(socket.socket, attribute="accept", return_value=(socket_listener, None))
        mocker.patch.object(socket.socket, attribute="send")

        requests_mock.add(
            method=authoriser.user_request.method.name,
            url=re.compile(str(authoriser.user_request.url)),
            repeat=True,
        )

        return "test-code"

    @pytest.fixture
    def mock_user_auth(self, authoriser: OAuth2AuthCode, mocker: MockerFixture) -> AsyncMock:
        return mocker.patch.object(
            authoriser, attribute="_authorise_user", side_effect=AsyncMock(return_value="test-code")
        )

    @pytest.fixture
    def mock_request_token(self, authoriser: OAuth2AuthCode, mocker: MockerFixture) -> AsyncMock:
        return mocker.patch.object(
            authoriser,
            attribute="_request_token",
            side_effect=AsyncMock(return_value={authoriser.response_handler.token_key: "request"})
        )

    @pytest.fixture
    def mock_refresh_token(self, authoriser: OAuth2AuthCode, mocker: MockerFixture) -> AsyncMock:
        return mocker.patch.object(
            authoriser,
            attribute="_refresh_token",
            side_effect=AsyncMock(return_value={authoriser.response_handler.token_key: "refresh"})
        )

    @pytest.fixture
    def mock_tester(self, authoriser: OAuth2AuthCode, mocker: MockerFixture) -> AsyncMock:
        return mocker.patch.object(
            authoriser, attribute="response_tester", side_effect=AsyncMock(return_value=True)
        )

    @pytest.fixture
    def mock_save(self, authoriser: OAuth2AuthCode, mocker: MockerFixture) -> AsyncMock:
        return mocker.patch.object(authoriser.response_handler, attribute="save_response_to_file")

    ###########################################################################
    ## User authorisation
    ###########################################################################
    async def test_authorise_user_successful(
            self, authoriser: OAuth2AuthCode, user_auth_code: str, mocker: MockerFixture
    ):
        def handle_user_request_successfully(url: str):
            """Check the URL given to the webopen call and patch socket response"""
            assert url.startswith(str(authoriser.user_request.url))
            assert unquote(URL(url).query["redirect_uri"]) == str(authoriser.redirect_uri)

            response = f"GET /?code={user_auth_code}&state={URL(url).query["state"]}"
            mocker.patch.object(socket.socket, attribute="recv", return_value=response.encode("utf-8"))

        authoriser.socket_handler.port = 8000
        mocker.patch(f"{MODULE_ROOT}.auth.oauth2.webopen", new=handle_user_request_successfully)

        async with ClientSession() as session:
            assert await authoriser._authorise_user(session) == user_auth_code

    async def test_authorise_user_with_bad_state_response(
            self, authoriser: OAuth2AuthCode, user_auth_code: str, mocker: MockerFixture
    ):
        def handle_user_request_with_bad_state(url: str):
            """Check the URL given to the webopen call and patch socket response"""
            assert url.startswith(str(authoriser.user_request.url))
            assert unquote(URL(url).query["redirect_uri"]) == str(authoriser.redirect_uri)

            response = f"GET /?code={user_auth_code}&state=BadState"
            mocker.patch.object(socket.socket, attribute="recv", return_value=response.encode("utf-8"))

        authoriser.socket_handler.port = 8001
        mocker.patch(f"{MODULE_ROOT}.auth.oauth2.webopen", new=handle_user_request_with_bad_state)

        with pytest.raises(AuthoriserError):
            async with ClientSession() as session:
                await authoriser._authorise_user(session)

    ###########################################################################
    ## Request/refresh token
    ###########################################################################
    @staticmethod
    def assert_response(actual: JSON, expected: JSON) -> None:
        assert {k: v for k, v in actual.items() if k not in response_enrich_keys} == expected
        assert "granted_at" in actual
        assert "expires_at" in actual

    async def test_request_token(self, authoriser: OAuth2AuthCode, auth_response: JSON, requests_mock: aioresponses):
        def exchange_response_for_token(*_, params: dict[str, str], **__) -> CallbackResult:
            assert params["redirect_uri"] == str(authoriser.redirect_uri)
            assert params["code"] == code

            return CallbackResult(payload=auth_response)

        code = "test-code"
        requests_mock.post(re.compile(str(authoriser.token_request.url)), callback=exchange_response_for_token)

        async with ClientSession() as session:
            response = await authoriser._request_token(session, code=code)

        self.assert_response(response, auth_response)
        assert "redirect_uri" not in getattr(authoriser.token_request, "params", {})
        assert "code" not in getattr(authoriser.token_request, "params", {})

    async def test_refresh_token(self, authoriser: OAuth2AuthCode, auth_response: JSON, requests_mock: aioresponses):
        def exchange_response_for_token(*_, params: dict[str, str], **__) -> CallbackResult:
            assert params["refresh_token"] == refresh_token
            return CallbackResult(payload=auth_response)

        refresh_token = "test-token"
        requests_mock.post(re.compile(str(authoriser.token_request.url)), callback=exchange_response_for_token)

        async with ClientSession() as session:
            response = await authoriser._refresh_token(session, refresh_token=refresh_token)

        self.assert_response(response, auth_response)
        assert "refresh_token" not in getattr(authoriser.token_request, "params", {})

    ###########################################################################
    ## Handle invalid loaded response
    ###########################################################################
    async def test_handle_invalid_loaded_response_with_no_refresh_token(
            self,
            authoriser: OAuth2AuthCode,
            auth_response: JSON,
            mock_user_auth: AsyncMock,
            mock_request_token: AsyncMock,
            mock_refresh_token: AsyncMock,
            mock_tester: AsyncMock,
    ):
        assert "refresh_token" not in auth_response
        result, valid = await authoriser._handle_invalid_loaded_response(auth_response)

        mock_user_auth.assert_called_once()
        mock_request_token.assert_called_once()
        mock_refresh_token.assert_not_called()
        mock_tester.assert_called_once()

        assert result == await mock_request_token()
        assert valid == await mock_tester()

    async def test_handle_invalid_loaded_response_with_no_refresh_request(
            self,
            authoriser: OAuth2AuthCode,
            auth_response: JSON,
            mock_user_auth: AsyncMock,
            mock_request_token: AsyncMock,
            mock_refresh_token: AsyncMock,
            mock_tester: AsyncMock,
    ):
        authoriser.refresh_request = None
        auth_response["refresh_token"] = "token"
        result, valid = await authoriser._handle_invalid_loaded_response(auth_response)

        mock_user_auth.assert_called_once()
        mock_request_token.assert_called_once()
        mock_refresh_token.assert_not_called()
        mock_tester.assert_called_once()

        assert result == await mock_request_token()
        assert valid == await mock_tester()

    async def test_handle_invalid_loaded_response_with_valid_refresh(
            self,
            authoriser: OAuth2AuthCode,
            auth_response: JSON,
            mock_user_auth: AsyncMock,
            mock_request_token: AsyncMock,
            mock_refresh_token: AsyncMock,
            mock_tester: AsyncMock,
    ):
        auth_response["refresh_token"] = "token"
        result, valid = await authoriser._handle_invalid_loaded_response(auth_response)

        mock_user_auth.assert_not_called()
        mock_request_token.assert_not_called()
        mock_refresh_token.assert_called_once()
        mock_tester.assert_called_once()

        assert result == await mock_refresh_token()
        assert valid == await mock_tester()

    async def test_handle_invalid_loaded_response_with_invalid_refresh(
            self,
            authoriser: OAuth2AuthCode,
            auth_response: JSON,
            mock_user_auth: AsyncMock,
            mock_request_token: AsyncMock,
            mock_refresh_token: AsyncMock,
            mocker: MockerFixture,
    ):
        async def tester(response: dict) -> bool:
            if response["access_token"] == "refresh":
                return False
            return True

        mocker.patch.object(authoriser, attribute="response_tester", new=tester)

        # with refresh token and good response
        auth_response["refresh_token"] = "token"
        result, valid = await authoriser._handle_invalid_loaded_response(auth_response)

        mock_user_auth.assert_called_once()
        mock_request_token.assert_called_once()
        mock_refresh_token.assert_called_once()

        assert result == await mock_request_token()
        assert valid

    ###########################################################################
    ## Main authorise method
    ###########################################################################
    async def test_authorise_uses_loaded_response(
            self,
            authoriser: OAuth2AuthCode,
            response_file_path: Path,
            auth_response: JSON,
            mock_user_auth: AsyncMock,
            mock_request_token: AsyncMock,
            mock_tester: AsyncMock,
            mock_save: AsyncMock,
    ):
        authoriser.response_handler.response = auth_response
        assert not authoriser.response_handler.file_path

        await authoriser.authorise()

        mock_user_auth.assert_not_called()
        mock_request_token.assert_not_called()
        mock_tester.assert_called_once()
        mock_save.assert_called_once()

    async def test_authorise_load_from_file(
            self,
            authoriser: OAuth2AuthCode,
            response_file_path: Path,
            mock_user_auth: AsyncMock,
            mock_request_token: AsyncMock,
            mock_tester: AsyncMock,
            mock_save: AsyncMock,
    ):
        assert not authoriser.response_handler.response
        authoriser.response_handler.file_path = response_file_path

        await authoriser.authorise()

        mock_user_auth.assert_not_called()
        mock_request_token.assert_not_called()
        mock_tester.assert_called_once()
        mock_save.assert_called_once()

    async def test_authorise_loaded_response_invalid(
            self,
            authoriser: OAuth2AuthCode,
            response_file_path: Path,
            auth_response: JSON,
            mock_user_auth: AsyncMock,
            mock_request_token: AsyncMock,
            mock_save: AsyncMock,
            mocker: MockerFixture,
    ):
        async def tester(response: dict) -> bool:
            if response[authoriser.response_handler.token_key] == "fake access token":
                return False
            return True

        mocker.patch.object(authoriser, attribute="response_tester", new=tester)
        mock_invalid_handler = mocker.patch.object(
            authoriser, attribute="_handle_invalid_loaded_response", return_value=(auth_response, True)
        )

        assert not authoriser.response_handler.response
        authoriser.response_handler.file_path = response_file_path
        mock_save = mocker.patch.object(authoriser.response_handler, attribute="save_response_to_file")

        await authoriser.authorise()

        mock_user_auth.assert_not_called()
        mock_request_token.assert_not_called()
        mock_invalid_handler.assert_called_once()
        mock_save.assert_called_once()

    async def test_authorise_new_token(
            self,
            authoriser: OAuth2AuthCode,
            response_file_path: Path,
            auth_response: JSON,
            mock_user_auth: AsyncMock,
            mock_request_token: AsyncMock,
            mock_tester: AsyncMock,
    ):
        assert not authoriser.response_handler.response
        assert not authoriser.response_handler.file_path

        await authoriser.authorise()

        mock_user_auth.assert_called_once()
        mock_request_token.assert_called_once()
        mock_tester.assert_called_once()

    async def test_authorise_no_response(
            self,
            authoriser: OAuth2AuthCode,
            response_file_path: Path,
            auth_response: JSON,
            mock_user_auth: AsyncMock,
            mocker: MockerFixture
    ):
        assert not authoriser.response_handler.response
        assert not authoriser.response_handler.file_path

        mocker.patch.object(authoriser, attribute="_request_token", return_value={})

        with pytest.raises(AuthoriserError, match="not generate or load"):
            await authoriser.authorise()

    async def test_authorise_invalid_response(
            self,
            authoriser: OAuth2AuthCode,
            response_file_path: Path,
            auth_response: JSON,
            mock_user_auth: AsyncMock,
            mock_request_token: AsyncMock,
            mocker: MockerFixture
    ):
        assert not authoriser.response_handler.response
        assert not authoriser.response_handler.file_path

        mocker.patch.object(authoriser, attribute="response_tester", side_effect=AsyncMock(return_value=False))

        with pytest.raises(AuthoriserError, match="still not valid"):
            await authoriser.authorise()
