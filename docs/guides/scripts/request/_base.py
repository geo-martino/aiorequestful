# noinspection PyUnresolvedReferences
import asyncio
# noinspection PyUnresolvedReferences
from typing import Any

# noinspection PyUnresolvedReferences
from yarl import URL

from aiorequestful.request import RequestHandler

request_handler: RequestHandler = RequestHandler.create()
api_url = "https://official-joke-api.appspot.com/jokes/programming/random"


async def send_get_request(handler: RequestHandler, url: str | URL) -> Any:
    """Sends a simple GET request using the given ``handler`` for the given ``url``."""
    async with handler:
        payload = await handler.get(url)

    return payload
