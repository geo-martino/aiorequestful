import json
import re
import socket
from copy import deepcopy
from datetime import datetime, timedelta
from http import HTTPMethod
from pathlib import Path
from time import sleep
from typing import Any

import pytest
from aiohttp import ClientSession, ClientResponse
from aioresponses import aioresponses, CallbackResult
from yarl import URL

from aiorequestful.auth.exception import AuthoriserError
from aiorequestful.auth.utils import AuthRequest, AuthResponse, AuthTester, SocketHandler
from aiorequestful.types import JSON, ImmutableHeaders
from tests.auth.utils import response_enrich_keys
from tests.utils import path_token


class TestAuthRequest:
    @pytest.fixture
    def auth_request(self) -> AuthRequest:
        return AuthRequest(
            method=HTTPMethod.GET,
            url="http://localhost:35000",
        )

    def test_sanitise_kwargs(self):
        kwargs = {
            "data": {
                "key1": "value1",
                "key2": 234,
                "key3": True,
            },
            "params": {
                "key1": 1.231,
                "key2": None,
                "key3": {},
            }
        }

        AuthRequest._sanitise_kwargs(kwargs)

        assert kwargs == {
            "data": {
                "key1": "value1",
                "key2": 234,
                "key3": "true",
            },
            "params": {
                "key1": 1.231,
                "key2": "null",
                "key3": {},
            }
        }

    @staticmethod
    def get_vars(obj: Any) -> dict[str, Any]:
        return {k: getattr(obj, k) for k in obj.__slots__ if hasattr(obj, k)}

    def test_determines_payload_key(self):
        params = {"key": "value"}
        request = AuthRequest(
            method=HTTPMethod.GET,
            url="http://localhost:35000",
            headers=params,
        )
        assert request._payload_key == "params"  # default value
        assert request.payload is None

        request = AuthRequest(
            method=HTTPMethod.GET,
            url="http://localhost:35000",
            params=params
        )
        assert request._payload_key == "params"
        assert request.payload == params

        request = AuthRequest(
            method=HTTPMethod.GET,
            url="http://localhost:35000",
            data=params
        )
        assert request._payload_key == "data"
        assert request.payload == params

        request = AuthRequest(
            method=HTTPMethod.GET,
            url="http://localhost:35000",
            json=params
        )
        assert request._payload_key == "json"
        assert request.payload == params

    def test_enrich_parameters(self, auth_request: AuthRequest):
        original = deepcopy(self.get_vars(auth_request))
        extension = {"code": 123}

        assert auth_request._payload_key == "params"
        assert not hasattr(auth_request, "params")
        assert not hasattr(auth_request, "headers")

        auth_request.enrich_payload(extension)
        assert self.get_vars(auth_request) == original

        with auth_request.enrich_payload(extension):
            assert self.get_vars(auth_request) != original
            assert hasattr(auth_request, "params")
            assert getattr(auth_request, "params") == extension

        auth_request.enrich_headers(extension)
        assert self.get_vars(auth_request) == original

        with auth_request.enrich_headers(extension):
            assert self.get_vars(auth_request) != original
            assert hasattr(auth_request, "headers")
            assert getattr(auth_request, "headers") == extension

        assert self.get_vars(auth_request) == original
        assert not hasattr(auth_request, "params")
        assert not hasattr(auth_request, "headers")

    def test_enrich_parameters_on_existing(self, auth_request: AuthRequest):
        auth_request.payload = {"key": "value"}
        auth_request.headers = {"header_key": "header_value"}
        original = deepcopy(self.get_vars(auth_request))
        extension = {"code": 123}

        auth_request.enrich_payload(extension)
        assert self.get_vars(auth_request) == original
        assert all(key not in auth_request.payload for key in extension)

        with auth_request.enrich_payload(extension):
            assert self.get_vars(auth_request) != original
            assert all(key in auth_request.payload for key in extension)
            assert auth_request.payload["code"] == extension["code"]

        auth_request.enrich_headers(extension)
        assert self.get_vars(auth_request) == original
        assert all(key not in auth_request.headers for key in extension)

        with auth_request.enrich_headers(extension):
            assert self.get_vars(auth_request) != original
            assert all(key in auth_request.headers for key in extension)
            assert auth_request.headers["code"] == extension["code"]

        assert self.get_vars(auth_request) == original
        assert all(key not in auth_request.payload for key in extension)
        assert all(key not in auth_request.headers for key in extension)

    async def test_request(self, auth_request: AuthRequest, requests_mock: aioresponses):
        actual = {}
        expected = {"key": "value"}

        def callback(_: URL, params: dict[str, Any], **__):
            actual.update(params)

        requests_mock.get(re.compile(str(auth_request.url)), callback=callback)
        with auth_request.enrich_payload(expected):
            async with ClientSession() as session:
                async with auth_request.request(session):
                    pass

        assert actual == expected


class TestAuthResponseHandler:

    @pytest.fixture
    def response(self) -> AuthResponse:
        return AuthResponse()

    @pytest.fixture(params=[path_token])
    def file_path(self, path: Path) -> Path:
        """Yield the temporary path for the token JSON file"""
        return path

    @pytest.fixture
    def auth_response(self, response: AuthResponse) -> JSON:
        return {
            response.token_key: "fake access token",
            "token_type": "Bearer",
            "expires_in": 3600,
            "scope": "test-read",
        }

    def test_get_token(self, response: AuthResponse, auth_response: JSON):
        # no response set
        assert not response
        with pytest.raises(AuthoriserError, match="not available"):
            assert response.token

        # no response contains invalid key
        response.replace({"key": "value"})
        assert response.token_key not in response
        with pytest.raises(AuthoriserError, match=response.token_key):
            assert response.token

        # valid response
        response.replace(auth_response)
        assert response.token == auth_response[response.token_key]

    def test_generate_headers(self, response: AuthResponse, auth_response: JSON):
        # no response set
        assert not response
        assert response.headers == {}

        response.replace(auth_response)
        assert len(response.headers) == 1
        assert response.headers["Authorization"] == f"{auth_response["token_type"]} {response.token}"

        response.token_prefix_default = "Basic"
        response.pop("token_type")
        assert response.headers["Authorization"] == f"Basic {response.token}"

        response.additional_headers = {"header1": "value1"}
        assert response.headers == {
            "Authorization": f"Basic {response.token}",
        } | response.additional_headers

    def test_sanitised_response(self, response: AuthResponse, auth_response: JSON):
        assert not response
        assert not response.sanitised

        auth_response["refresh_token"] = "this is a very secret refresh token"
        assert response.token_key in auth_response

        response.replace(auth_response)
        result = response.sanitised
        assert result[response.token_key] != auth_response[response.token_key]

        token_keys = [key for key in result if key.endswith("_token")]
        assert len(token_keys) > 1
        assert all(auth_response[key] != result[key] for key in token_keys)

        # processes stored response if response not given
        response.replace(auth_response)
        assert response.sanitised == result

    def test_enrich_response(self, response: AuthResponse, auth_response: JSON):
        assert not response
        assert all(key not in auth_response for key in response_enrich_keys)

        response._response = auth_response
        response.enrich(refresh_token="i am a refresh token")
        assert all(key in response for key in response_enrich_keys)

        sleep(0.1)
        response._response = deepcopy(auth_response)
        response.enrich(refresh_token="this is a very secret refresh token")

        # overwrites these keys
        for key in ("granted_at", "expires_at"):
            assert response[key] != auth_response[key]

        # does not overwrite these keys
        for key in ("refresh_token",):
            assert response[key] == auth_response[key]

    def test_load_response_from_file(self, response: AuthResponse, auth_response: JSON, file_path: Path):
        # does nothing when no file path given
        assert not response.file_path
        assert not response.load_response_from_file()
        assert not response

        # does nothing when non-existent path given
        response.file_path = file_path.with_name("i do not exist")
        assert not response.load_response_from_file()
        assert not response

        response.file_path = file_path
        assert response.load_response_from_file() == response
        response_reduced = {k: v for k, v in response.items() if k not in response_enrich_keys}
        assert response_reduced == auth_response

    def test_save_response_to_file(self, response: AuthResponse, auth_response: JSON, tmp_path: Path):
        # does nothing when no file path given
        assert not response.file_path
        response.save_response_to_file()
        assert not response

        # does nothing when no response given
        file_path = tmp_path.joinpath("path").joinpath("to").joinpath("token").with_suffix(".json")
        response.file_path = file_path
        assert not response
        response.save_response_to_file()
        assert not response.file_path.exists()

        # saves and updates stored response
        response.replace(auth_response)
        response.save_response_to_file()
        assert response == auth_response
        with open(response.file_path, "r") as f:
            assert json.load(f) == auth_response

        # saves and updates stored response for new response
        response_new = {"key1": "value1"}
        assert response_new != auth_response

        response.replace(response_new)
        response.save_response_to_file()
        with open(response.file_path, "r") as f:
            response_file = json.load(f)

        assert response_file == response_new
        assert response_file != auth_response


class TestAuthTester:
    @pytest.fixture
    def tester(self) -> AuthTester:
        return AuthTester()

    @pytest.fixture
    def test_request(self) -> AuthRequest:
        return AuthRequest(
            method=HTTPMethod.GET,
            url="http://localhost:35000",
        )

    @staticmethod
    async def response_test(response: ClientResponse) -> bool:
        return "error" not in await response.text()

    @staticmethod
    def callback(*_, headers: ImmutableHeaders, **__) -> CallbackResult:
        if headers["Authorization"] == "Bearer valid":
            return CallbackResult(payload={"result": "success!"})
        return CallbackResult(payload={"error": "message"})

    def test_response(self, tester: AuthTester):
        assert tester._test_response({"result": "valid"})
        assert not tester._test_response({"error": "message"})

    def test_expiry(self, tester: AuthTester):
        # defaults to valid when test not set to run
        assert not tester.max_expiry
        assert tester._test_expiry({"expires_at": (datetime.now() + timedelta(seconds=1)).timestamp()})
        tester.max_expiry = 1000
        assert tester._test_expiry({"key": "id not contain valid keys to run the test"})

        response = {
            "access_token": "fake access token",
            "token_type": "Bearer",
            "expires_in": 3600,
            "scope": "test-read",
        }
        tester.max_expiry = 1500
        assert tester._test_expiry(response)

        response["expires_in"] = 100
        assert not tester._test_expiry(response)

        # expires_at value takes priority
        response["expires_at"] = (datetime.now() + timedelta(seconds=3600)).timestamp()
        assert tester._test_expiry(response)

        response["expires_at"] = (datetime.now() + timedelta(seconds=100)).timestamp()
        assert not tester._test_expiry(response)

    async def test_token(
            self, tester: AuthTester, test_request: AuthRequest, requests_mock: aioresponses
    ):
        # defaults to valid when test not set to run
        assert not tester.request
        assert await tester._test_token(None)
        assert await tester._test_token({"Authorization": "Basic invalid"})

        tester.request = test_request
        tester.response_test = self.response_test
        requests_mock.get(re.compile(str(test_request.url)), callback=self.callback, repeat=True)

        assert await tester._test_token({"Authorization": "Bearer valid"})
        assert not await tester._test_token({"Authorization": "Basic invalid"})

    async def test_all(self, tester: AuthTester, test_request: AuthRequest):
        response = AuthResponse()
        response.update({
            "result": "valid",
            "expires_at": (datetime.now() + timedelta(seconds=3000)).timestamp()
        })
        assert await tester(response)

        tester.request = test_request
        tester.response_test = self.response_test
        tester.max_expiry = 5000

        assert not await tester(response)


class TestSocketHandler:

    @pytest.fixture
    def socket_handler(self) -> SocketHandler:
        return SocketHandler()

    def test_context_management(self, socket_handler: SocketHandler):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            assert s.connect_ex(('localhost', socket_handler.port)) != 0  # socket can be opened

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s, socket_handler:
            assert s.connect_ex(('localhost', socket_handler.port)) == 0  # socket cannot be opened

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            assert s.connect_ex(('localhost', socket_handler.port)) != 0  # socket can be opened
