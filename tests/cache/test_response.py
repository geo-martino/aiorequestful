import json
from http import HTTPMethod
from typing import Any

import pytest
from aiohttp import ClientRequest
from yarl import URL

from aiorequestful.cache.response import CachedResponse


class TestCachedResponse:

    @pytest.fixture(scope="class")
    def http_request(self) -> ClientRequest:
        """Yields a basic :py:class:`ClientRequest` as a pytest.fixture."""
        return ClientRequest(
            method=HTTPMethod.GET.name, url=URL("https://www.test.com"), headers={"Content-Type": "application/json"}
        )

    @pytest.fixture(scope="class")
    def payload(self) -> dict[str, Any]:
        """Yields the expected payload dict response for a given request as a pytest.fixture."""
        return {
            "1": "val1",
            "2": "val2",
            "3": "val3",
        }

    @pytest.fixture
    def http_response(self, http_request: ClientRequest, payload: dict[str, Any]) -> CachedResponse:
        """Yields the expected response for a given request as a pytest.fixture."""
        return CachedResponse(request=http_request, payload=json.dumps(payload))

    async def test_read(self, http_response: CachedResponse, payload: dict[str, Any]):
        assert await http_response.read() == json.dumps(payload).encode()
        assert await http_response.text() == json.dumps(payload)
        assert await http_response.json() == payload
