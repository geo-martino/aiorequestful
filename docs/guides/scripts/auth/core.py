import asyncio

from aiorequestful.auth import Authoriser

authoriser = Authoriser()


async def auth(a: Authoriser) -> None:
    headers = await a.authorise()

    # all the following commands are just aliases for the `authorise` method
    headers = await a
    headers = await a()


asyncio.run(auth(authoriser))
