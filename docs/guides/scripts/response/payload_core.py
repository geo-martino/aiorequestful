import asyncio
from typing import Any

from aiorequestful.response.payload import PayloadHandler


async def handle(handler: PayloadHandler, payload: Any) -> None:
    print(await handler.serialize(payload))  # convert the payload data to a string
    print(await handler.deserialize(payload))  # convert the payload data to the required object type

asyncio.run(handle(handler=PayloadHandler(), payload='{"key": "value"}'))
