"""
Resources to handle manipulation of payload data returned by responses into Python objects.
"""
import json
from abc import ABC, abstractmethod
from collections.abc import Awaitable
from typing import Any

from aiohttp import ClientResponse

from aiorequestful.response.exception import PayloadHandlerError
from aiorequestful.types import JSON


class PayloadHandler[T: Any](ABC):
    """Handles payload data conversion to return response payload in expected format."""

    __slots__ = ()

    @abstractmethod
    async def serialize(self, payload: str | bytes | bytearray | T) -> str:
        """Serialize the payload object to a string."""
        raise NotImplementedError

    @abstractmethod
    async def deserialize(self, response: str | bytes | bytearray | ClientResponse | T) -> T:
        """
        Extract payload data from the given ``response`` and serialize to the appropriate object.

        :param response: The response/payload to handle.
        :raise PayloadHandlerError: When the input data is not recognised.
        """
        raise NotImplementedError

    def __call__(self, response: str | bytes | bytearray | ClientResponse | T) -> Awaitable[T]:
        return self.deserialize(response=response)


class JSONPayloadHandler(PayloadHandler[JSON]):

    __slots__ = ("indent",)

    def __init__(self, indent: int = None):
        self.indent = indent

    async def serialize(self, payload: str | bytes | bytearray | JSON) -> str:
        if isinstance(payload, str | bytes | bytearray):
            try:
                payload = json.loads(payload)
            except (json.decoder.JSONDecodeError, TypeError):
                raise PayloadHandlerError(f"Unrecognised input type: {payload}")
        return json.dumps(payload, indent=self.indent)

    async def deserialize(self, response: str | bytes | bytearray | ClientResponse | JSON) -> JSON:
        match response:
            case dict():
                try:  # check the given payload can be converted to/from JSON format
                    return json.loads(json.dumps(response))
                except (json.decoder.JSONDecodeError, TypeError):
                    raise PayloadHandlerError("Given payload is not a valid JSON object")
            case str() | bytes() | bytearray():
                return json.loads(response)
            case ClientResponse():
                return await response.json(content_type=None)
            case _:
                raise PayloadHandlerError(f"Unrecognised input type: {response}")


class StringPayloadHandler(PayloadHandler[str]):

    __slots__ = ()

    async def serialize(self, payload: str | bytes | bytearray) -> str:
        if isinstance(payload, bytes | bytearray):
            return payload.decode()
        return str(payload)

    async def deserialize(self, response: str | bytes | bytearray | ClientResponse) -> str:
        match response:
            case str():
                return response
            case bytes() | bytearray():
                return response.decode()
            case ClientResponse():
                return await response.text()
            case None:
                raise PayloadHandlerError(f"Unrecognised input type: {response}")
            case _:
                return str(response)
