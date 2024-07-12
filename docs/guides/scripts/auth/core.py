# BASIC

import asyncio

from aiorequestful.auth import Authoriser

authoriser = Authoriser(service_name="http service")


async def authorise(auth: Authoriser) -> None:
    headers = await auth.authorise()

    # all the following commands are just aliases for the `authorise` method
    headers = await auth
    headers = await auth()


asyncio.run(authorise(authoriser))

# END
