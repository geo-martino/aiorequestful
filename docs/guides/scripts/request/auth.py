from docs.guides.scripts.request._base import *

# ASSIGNMENT

from aiorequestful.auth.basic import BasicAuthoriser


async def auth_and_send_get_request(handler: RequestHandler, url: str) -> Any:
    """Authorise the ``handler`` with the service before sending a GET request to the given ``url``."""
    async with handler:
        await handler.authorise()
        payload = await handler.get(url)

    return payload


authoriser = BasicAuthoriser(login="username", password="password")
request_handler.authoriser = authoriser

task = auth_and_send_get_request(request_handler, url=api_url)
result = asyncio.run(task)

print(result)

# END
# INSTANTIATION

request_handler = RequestHandler.create(authoriser=authoriser)

task = auth_and_send_get_request(request_handler, url=api_url)
result = asyncio.run(task)

print(result)

# END
