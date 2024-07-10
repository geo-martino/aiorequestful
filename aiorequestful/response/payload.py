from abc import ABC, abstractmethod
from collections.abc import Awaitable
from typing import Any

from aiohttp import ClientResponse

from aiorequestful.types import JSON


class PayloadHandler[T: Any](ABC):
    """Handles payload data conversion to return response payload in expected format."""

    __slots__ = ()

    @abstractmethod
    async def serialise(self, response: ClientResponse) -> T:
        """Extract payload data from the given ``response`` and serialise to the appropriate object."""
        raise NotImplementedError

    def __call__(self, response: ClientResponse) -> Awaitable[T]:
        return self.serialise(response=response)


class JSONPayloadHandler(PayloadHandler):

    __slots__ = ()

    async def serialise(self, response: ClientResponse) -> JSON:
        return await response.json(content_type=None)


class StringPayloadHandler(PayloadHandler):

    __slots__ = ()

    async def serialise(self, response: ClientResponse) -> str:
        return await response.text()
