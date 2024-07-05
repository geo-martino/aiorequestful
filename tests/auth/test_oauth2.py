import re
import socket
from unittest.mock import AsyncMock
from urllib.parse import unquote

import pytest
from aiohttp import ClientSession
from aioresponses import aioresponses, CallbackResult
from pytest_mock import MockerFixture
from yarl import URL

from aiorequestful import MODULE_ROOT
from aiorequestful.auth import AuthRequest, AuthResponseHandler, AuthResponseTester
from aiorequestful.auth.oauth2 import OAuth2AuthCode
from aiorequestful.exception import AuthoriserError
from aiorequestful.types import Method, JSON
from tests.auth.utils import response_enrich_keys


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
        response_handler = AuthResponseHandler(

        )
        response_tester = AuthResponseTester(

        )
        return OAuth2AuthCode(
            service_name="test",
            user_request=user_request,
            token_request=token_request,
            refresh_request=refresh_request,
            response_handler=response_handler,
            response_tester=response_tester,
            user_request_redirect_url=URL("http://localhost/redirect"),
            user_request_redirect_local_port=8080,
        )

    @pytest.fixture
    def auth_response(self) -> JSON:
        return {
            "access_token": "fake access token",
            "token_type": "Bearer",
            "expires_in": 3600,
            "scope": "test-read",
        }

    async def test_authorise_user(self, authoriser: OAuth2AuthCode, mocker: MockerFixture, requests_mock: aioresponses):
        socket_listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        mocker.patch.object(socket.socket, attribute="accept", return_value=(socket_listener, None))
        mocker.patch.object(socket.socket, attribute="send")
        code = "test-code"

        def handle_user_request_successfully(url: str):
            """Check the URL given to the webopen call and patch socket response"""
            assert url.startswith(str(authoriser.user_request.url))
            assert unquote(URL(url).query["redirect_uri"]) == str(authoriser.user_request_redirect_url)

            response = f"GET /?code={code}&state={URL(url).query["state"]}"
            mocker.patch.object(socket.socket, attribute="recv", return_value=response.encode("utf-8"))

        requests_mock.add(
            method=authoriser.user_request.method.name,
            url=re.compile(str(authoriser.user_request.url)),
            repeat=True,
        )

        # successful request
        mocker.patch(f"{MODULE_ROOT}.auth.oauth2.webopen", new=handle_user_request_successfully)
        async with ClientSession() as session:
            assert await authoriser._authorise_user(session) == code

        # bad state response
        def handle_user_request_with_bad_state(url: str):
            """Check the URL given to the webopen call and patch socket response"""
            assert url.startswith(str(authoriser.user_request.url))
            assert unquote(URL(url).query["redirect_uri"]) == str(authoriser.user_request_redirect_url)

            response = f"GET /?code={code}&state=BadState"
            mocker.patch.object(socket.socket, attribute="recv", return_value=response.encode("utf-8"))

        mocker.patch(f"{MODULE_ROOT}.auth.oauth2.webopen", new=handle_user_request_with_bad_state)
        with pytest.raises(AuthoriserError):
            async with ClientSession() as session:
                await authoriser._authorise_user(session)

    @staticmethod
    def assert_response(actual: JSON, expected: JSON) -> None:
        assert {k: v for k, v in actual.items() if k not in response_enrich_keys} == expected
        assert "granted_at" in actual
        assert "expires_at" in actual

    async def test_request_token(self, authoriser: OAuth2AuthCode, auth_response: JSON, requests_mock: aioresponses):
        def exchange_response_for_token(*_, params: dict[str, str], **__) -> CallbackResult:
            assert params["redirect_uri"] == str(authoriser.user_request_redirect_url)
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

    @pytest.fixture
    def mock_user_auth(self, authoriser: OAuth2AuthCode, mocker: MockerFixture) -> AsyncMock:
        return mocker.patch.object(
            authoriser, attribute="_authorise_user", side_effect=AsyncMock(return_value="test-code")
        )

    @pytest.fixture
    def mock_request_token(self, authoriser: OAuth2AuthCode, mocker: MockerFixture) -> AsyncMock:
        return mocker.patch.object(
            authoriser, attribute="_request_token", side_effect=AsyncMock(return_value={"token": "request"})
        )

    @pytest.fixture
    def mock_refresh_token(self, authoriser: OAuth2AuthCode, mocker: MockerFixture) -> AsyncMock:
        return mocker.patch.object(
            authoriser, attribute="_refresh_token", side_effect=AsyncMock(return_value={"token": "refresh"})
        )

    @pytest.fixture
    def mock_tester(self, authoriser: OAuth2AuthCode, mocker: MockerFixture) -> AsyncMock:
        return mocker.patch.object(
            authoriser, attribute="response_tester", side_effect=AsyncMock(return_value=True)
        )

    async def test_handle_invalid_loaded_response_with_no_refresh_token(
            self,
            authoriser: OAuth2AuthCode,
            auth_response: JSON,
            mock_user_auth: AsyncMock,
            mock_request_token: AsyncMock,
            mock_refresh_token: AsyncMock,
            mock_tester: AsyncMock,
    ):
        # no refresh token
        assert "refresh_token" not in auth_response
        result, valid = await authoriser._handle_invalid_loaded_response(auth_response)

        assert mock_user_auth.call_count == 1
        assert mock_request_token.call_count == 1
        assert mock_refresh_token.call_count == 0
        assert mock_tester.call_count == 1

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

        assert mock_user_auth.call_count == 1
        assert mock_request_token.call_count == 1
        assert mock_refresh_token.call_count == 0
        assert mock_tester.call_count == 1

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
        # with refresh token and good response
        auth_response["refresh_token"] = "token"
        result, valid = await authoriser._handle_invalid_loaded_response(auth_response)

        assert mock_user_auth.call_count == 0
        assert mock_request_token.call_count == 0
        assert mock_refresh_token.call_count == 1
        assert mock_tester.call_count == 1

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
        # with refresh token and bad response
        async def tester(response: dict) -> bool:
            print(response)
            if response["token"] == "refresh":
                return False
            return True

        mocker.patch.object(authoriser, attribute="response_tester", new=tester)

        # with refresh token and good response
        auth_response["refresh_token"] = "token"
        result, valid = await authoriser._handle_invalid_loaded_response(auth_response)

        assert mock_user_auth.call_count == 1
        assert mock_request_token.call_count == 1
        assert mock_refresh_token.call_count == 1

        assert result == await mock_request_token()
        assert valid

    async def test_authorise(self, authoriser: OAuth2AuthCode, auth_response: JSON, requests_mock: aioresponses):
        pass
