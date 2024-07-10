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

from aiorequestful.auth import AuthRequest, AuthResponseHandler, AuthResponseTester, SocketHandler
from aiorequestful.auth.exception import AuthoriserError
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

    def test_enrich_parameters(self, auth_request: AuthRequest):

        original = deepcopy(self.get_vars(auth_request))
        extension = {"code": 123}
        assert not hasattr(auth_request, "params")

        auth_request.enrich_parameters("params", extension)
        assert self.get_vars(auth_request) == original

        with auth_request.enrich_parameters("params", extension):
            assert self.get_vars(auth_request) != original
            assert hasattr(auth_request, "params")
            assert getattr(auth_request, "params") == extension

        assert self.get_vars(auth_request) == original
        assert not hasattr(auth_request, "params")

    def test_enrich_parameters_on_existing(self, auth_request: AuthRequest):
        auth_request.params = {"key": "value"}
        original = deepcopy(self.get_vars(auth_request))
        extension = {"code": 123}

        auth_request.enrich_parameters("params", extension)
        assert self.get_vars(auth_request) == original
        assert all(key not in auth_request.params for key in extension)

        with auth_request.enrich_parameters("params", extension):
            assert self.get_vars(auth_request) != original
            assert all(key in auth_request.params for key in extension)
            assert auth_request.params["code"] == extension["code"]

        assert self.get_vars(auth_request) == original
        assert all(key not in auth_request.params for key in extension)

    async def test_request(self, auth_request: AuthRequest, requests_mock: aioresponses):
        actual = {}
        expected = {"key": "value"}

        def callback(_: URL, params: dict[str, Any], **__):
            actual.update(params)

        requests_mock.get(re.compile(str(auth_request.url)), callback=callback)
        with auth_request.enrich_parameters("params", expected):
            async with ClientSession() as session:
                async with auth_request.request(session):
                    pass

        assert actual == expected


class TestAuthResponseHandler:

    @pytest.fixture
    def response_handler(self) -> AuthResponseHandler:
        return AuthResponseHandler()

    @pytest.fixture(params=[path_token])
    def file_path(self, path: Path) -> Path:
        """Yield the temporary path for the token JSON file"""
        return path

    @pytest.fixture
    def response(self, response_handler: AuthResponseHandler) -> JSON:
        return {
            response_handler.token_key: "fake access token",
            "token_type": "Bearer",
            "expires_in": 3600,
            "scope": "test-read",
        }

    def test_get_token(self, response_handler: AuthResponseHandler, response: JSON):
        # no response set
        assert not response_handler.response
        with pytest.raises(AuthoriserError, match="not available"):
            assert response_handler.token

        # no response contains invalid key
        response_handler.response = {"key": "value"}
        assert response_handler.token_key not in response_handler.response
        with pytest.raises(AuthoriserError, match=response_handler.token_key):
            assert response_handler.token

        # valid response
        response_handler.response = response
        assert response_handler.token == response[response_handler.token_key]

    def test_generate_headers(self, response_handler: AuthResponseHandler, response: JSON):
        response_handler.response = response
        assert len(response_handler.headers) == 1
        assert response_handler.headers["Authorization"] == f"{response["token_type"]} {response_handler.token}"

        response_handler.token_prefix_default = "Basic"
        response.pop("token_type")
        assert response_handler.headers["Authorization"] == f"Basic {response_handler.token}"

        response_handler.additional_headers = {"header1": "value1"}
        assert response_handler.headers == {
            "Authorization": f"Basic {response_handler.token}",
        } | response_handler.additional_headers

    def test_sanitise_response(self, response_handler: AuthResponseHandler, response: JSON):
        assert not response_handler.response

        response["refresh_token"] = "this is a very secret refresh token"
        assert response_handler.token_key in response

        result = response_handler.sanitise_response(response)
        assert result[response_handler.token_key] != response[response_handler.token_key]

        token_keys = [key for key in result if key.endswith("_token")]
        assert len(token_keys) > 1
        assert all(response[key] != result[key] for key in token_keys)

        # processes stored response if response not given
        response_handler.response = response
        assert response_handler.sanitise_response() == result

    def test_enrich_response(self, response_handler: AuthResponseHandler, response: JSON):
        assert not response_handler.response
        assert all(key not in response for key in response_enrich_keys)

        response_handler.enrich_response(response, refresh_token="i am a refresh token")
        assert all(key in response for key in response_enrich_keys)

        sleep(0.1)
        response_handler.response = deepcopy(response)
        response_handler.enrich_response(refresh_token="this is a very secret refresh token")

        # overwrites these keys
        for key in ("granted_at", "expires_at"):
            assert response_handler.response[key] != response[key]

        # does not overwrite these keys
        for key in ("refresh_token",):
            assert response_handler.response[key] == response[key]

    def test_load_response_from_file(self, response_handler: AuthResponseHandler, response: JSON, file_path: Path):
        # does nothing when no file path given
        assert not response_handler.file_path
        assert not response_handler.load_response_from_file()
        assert not response_handler.response

        # does nothing when non-existent path given
        response_handler.file_path = file_path.with_name("i do not exist")
        assert not response_handler.load_response_from_file()
        assert not response_handler.response

        response_handler.file_path = file_path
        assert response_handler.load_response_from_file() == response_handler.response
        response_reduced = {k: v for k, v in response_handler.response.items() if k not in response_enrich_keys}
        assert response_reduced == response

    def test_save_response_to_file(self, response_handler: AuthResponseHandler, response: JSON, tmp_path: Path):
        # does nothing when no file path given
        assert not response_handler.file_path
        response_handler.save_response_to_file()
        assert not response_handler.response

        # does nothing when no response given
        file_path = tmp_path.joinpath("token").with_suffix(".json")
        response_handler.file_path = file_path
        assert not response_handler.response
        response_handler.save_response_to_file()
        assert not response_handler.file_path.exists()

        # saves and updates stored response
        response_handler.save_response_to_file(response)
        assert response_handler.response == response
        with open(response_handler.file_path, "r") as f:
            assert json.load(f) == response

        # saves and updates stored response for new response
        response_new = {"key1": "value1"}
        assert response_new != response

        response_handler.save_response_to_file(response_new)
        assert response_handler.response == response_new
        with open(response_handler.file_path, "r") as f:
            response_file = json.load(f)

        assert response_file == response_new
        assert response_file != response


class TestAuthResponseTester:
    @pytest.fixture
    def response_tester(self) -> AuthResponseTester:
        return AuthResponseTester()

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

    def test_response(self, response_tester: AuthResponseTester):
        assert response_tester._test_response({"result": "valid"})
        assert not response_tester._test_response({"error": "message"})

    def test_expiry(self, response_tester: AuthResponseTester):
        # defaults to valid when test not set to run
        assert not response_tester.max_expiry
        assert response_tester._test_expiry({"expires_at": (datetime.now() + timedelta(seconds=1)).timestamp()})
        response_tester.max_expiry = 1000
        assert response_tester._test_expiry({"key": "id not contain valid keys to run the test"})

        response = {
            "access_token": "fake access token",
            "token_type": "Bearer",
            "expires_in": 3600,
            "scope": "test-read",
        }
        response_tester.max_expiry = 1500
        assert response_tester._test_expiry(response)

        response["expires_in"] = 100
        assert not response_tester._test_expiry(response)

        # expires_at value takes priority
        response["expires_at"] = (datetime.now() + timedelta(seconds=3600)).timestamp()
        assert response_tester._test_expiry(response)

        response["expires_at"] = (datetime.now() + timedelta(seconds=100)).timestamp()
        assert not response_tester._test_expiry(response)

    async def test_token(
            self, response_tester: AuthResponseTester, test_request: AuthRequest, requests_mock: aioresponses
    ):
        # defaults to valid when test not set to run
        assert not response_tester.request
        assert await response_tester._test_token(None)
        assert await response_tester._test_token({"Authorization": "Basic invalid"})

        response_tester.request = test_request
        response_tester.response_test = self.response_test
        requests_mock.get(re.compile(str(test_request.url)), callback=self.callback, repeat=True)

        assert await response_tester._test_token({"Authorization": "Bearer valid"})
        assert not await response_tester._test_token({"Authorization": "Basic invalid"})

    async def test_all(self, response_tester: AuthResponseTester, test_request: AuthRequest):
        assert await response_tester(
            response={
                "result": "valid",
                "expires_at": (datetime.now() + timedelta(seconds=3000)).timestamp()
            },
            headers={"Authorization": "Basic invalid"}
        )

        response_tester.request = test_request
        response_tester.response_test = self.response_test
        response_tester.max_expiry = 5000

        assert not await response_tester(
            response={
                "result": "valid",
                "expires_at": (datetime.now() + timedelta(seconds=3000)).timestamp()
            },
            headers={"Authorization": "Basic invalid"}
        )


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
