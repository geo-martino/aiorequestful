# PART 0

import asyncio
from typing import Any

from aiorequestful.response.payload import PayloadHandler


async def handle(handler: PayloadHandler, payload: Any) -> None:
    print(await handler.serialize(payload))  # convert the payload data to a string
    print(await handler.deserialize(payload))  # convert the payload data to the required object type

asyncio.run(handle(handler=PayloadHandler(), payload='{"key": "value"}'))

# PART 1

from aiorequestful.response.payload import StringPayloadHandler

payload_data = {"key": "value"}
payload_handler = StringPayloadHandler()


async def handle(handler: PayloadHandler, payload: Any) -> None:
    print(await handler.serialize(payload))  # convert the payload data to a string
    print(await handler.deserialize(payload))  # convert the payload data to a string

asyncio.run(handle(handler=payload_handler, payload=payload_data))

# PART 2

from aiorequestful.response.payload import JSONPayloadHandler

payload_data = '{"key": "value"}'
payload_handler = JSONPayloadHandler()


async def handle(handler: PayloadHandler, payload: Any) -> None:
    print(await handler.serialize(payload))  # convert the payload data to a string
    print(await handler.deserialize(payload))  # convert the payload data to a dict

asyncio.run(handle(handler=payload_handler, payload=payload_data))
