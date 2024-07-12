# PART 1

import asyncio
from typing import Any

from yarl import URL

from aiorequestful.request import RequestHandler


async def send_get_request(handler: RequestHandler, url: str | URL) -> Any:
    """Sends a simple GET request using the given ``handler`` for the given ``url``."""
    async with handler:
        payload = await handler.get(url)

    return payload


request_handler: RequestHandler = RequestHandler.create()
api_url = "https://official-joke-api.appspot.com/jokes/programming/random"

task = send_get_request(request_handler, url=api_url)
result = asyncio.run(task)

print(result)
print(type(result).__name__)


# PART 2

async def send_get_requests(handler: RequestHandler, url: str | URL, count: int = 20) -> tuple[Any]:
    async with handler:
        payloads = await asyncio.gather(*[handler.get(url) for _ in range(count)])

    return payloads

results = asyncio.run(send_get_requests(request_handler, url=api_url, count=20))
for result in results:
    print(result)
