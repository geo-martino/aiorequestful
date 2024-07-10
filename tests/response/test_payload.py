import json
from abc import ABC, abstractmethod
from typing import Any

import pytest
from aiohttp import ClientResponse

from aiorequestful.response.payload import PayloadHandler, JSONPayloadHandler, StringPayloadHandler
from aiorequestful.types import JSON


class PayloadHandlerTester(ABC):

    @abstractmethod
    def handler(self) -> PayloadHandler:
        raise NotImplementedError

    @abstractmethod
    def payload(self) -> Any:
        raise NotImplementedError

    @abstractmethod
    def payload_encoded(self, payload: Any) -> bytes:
        raise NotImplementedError

    @pytest.fixture
    def response(self, dummy_response: ClientResponse, payload_encoded: bytes) -> ClientResponse:
        dummy_response.content.feed_data(payload_encoded)
        dummy_response.content.feed_eof()
        return dummy_response

    @staticmethod
    async def test_serialise(handler: PayloadHandler, response: ClientResponse, payload: Any):
        assert await handler.deserialize(response) == payload


class TestJSONPayloadHandler(PayloadHandlerTester):

    @pytest.fixture
    def handler(self) -> JSONPayloadHandler:
        return JSONPayloadHandler()

    @pytest.fixture
    def payload(self) -> JSON:
        return {"key": "value"}

    @pytest.fixture
    def payload_encoded(self, payload: Any) -> bytes:
        return json.dumps(payload).encode()


class TestStringPayloadHandler(PayloadHandlerTester):

    @pytest.fixture
    def handler(self) -> StringPayloadHandler:
        return StringPayloadHandler()

    @pytest.fixture
    def payload(self) -> str:
        return "I am a payload"

    @pytest.fixture
    def payload_encoded(self, payload: Any) -> bytes:
        return payload.encode()
