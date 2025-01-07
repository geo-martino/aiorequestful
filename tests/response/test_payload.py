import json
from abc import ABC, abstractmethod
from typing import Any

import pytest
from aiohttp import ClientResponse

from aiorequestful.response.exception import PayloadHandlerError
from aiorequestful.response.payload import PayloadHandler, JSONPayloadHandler, StringPayloadHandler, BytesPayloadHandler
from aiorequestful.types import JSON


class PayloadHandlerTester(ABC):

    @abstractmethod
    def handler(self) -> PayloadHandler:
        raise NotImplementedError

    @abstractmethod
    def payload(self) -> Any:
        raise NotImplementedError

    @abstractmethod
    def payload_serialized(self, payload: Any) -> str:
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
    async def test_serialize(
            handler: PayloadHandler,
            response: ClientResponse,
            payload: Any,
            payload_serialized: str,
            payload_encoded: bytes,
    ):
        assert await handler.serialize(payload) == payload_serialized
        assert await handler.serialize(payload_serialized) == payload_serialized
        assert await handler.serialize(payload_encoded) == payload_serialized
        assert await handler.serialize(bytearray(payload_encoded)) == payload_serialized

    @staticmethod
    async def test_deserialize(
            handler: PayloadHandler,
            response: ClientResponse,
            payload: Any,
            payload_serialized: str,
            payload_encoded: bytes,
    ):
        assert await handler.deserialize(payload) == payload
        assert await handler.deserialize(payload_serialized) == payload
        assert await handler.deserialize(payload_encoded) == payload
        assert await handler.deserialize(bytearray(payload_encoded)) == payload
        assert await handler.deserialize(response) == payload

        with pytest.raises(PayloadHandlerError):
            await handler.deserialize(None)


class TestStringPayloadHandler(PayloadHandlerTester):

    @pytest.fixture
    def handler(self) -> StringPayloadHandler:
        return StringPayloadHandler()

    @pytest.fixture
    def payload(self) -> str:
        return "I am a payload"

    @pytest.fixture
    def payload_serialized(self, payload: Any) -> str:
        return payload

    @pytest.fixture
    def payload_encoded(self, payload: Any) -> bytes:
        return payload.encode()


class TestBytesPayloadHandler(PayloadHandlerTester):

    @pytest.fixture
    def handler(self) -> BytesPayloadHandler:
        return BytesPayloadHandler()

    @pytest.fixture
    def payload(self) -> bytes:
        return "I am a payload".encode()

    @pytest.fixture
    def payload_serialized(self, payload: bytes) -> str:
        return payload.decode()

    @pytest.fixture
    def payload_encoded(self, payload: bytes) -> bytes:
        return payload


class TestJSONPayloadHandler(PayloadHandlerTester):

    @pytest.fixture
    def handler(self) -> JSONPayloadHandler:
        return JSONPayloadHandler()

    @pytest.fixture
    def payload(self) -> JSON:
        return {"key": "value"}

    @pytest.fixture
    def payload_serialized(self, payload: Any) -> str:
        return json.dumps(payload)

    @pytest.fixture
    def payload_encoded(self, payload: Any) -> bytes:
        return json.dumps(payload).encode()
