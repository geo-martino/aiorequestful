# SETTINGS

from http import HTTPMethod
from typing import Any
from yarl import URL

from aiorequestful.cache.backend.base import ResponseRepositorySettings


class SpotifyRepositorySettings(ResponseRepositorySettings):

    @property
    def fields(self) -> tuple[str, ...]:
        return "id", "version"

    def get_key(self, method: str | HTTPMethod, url: str | URL, **__) -> tuple[str | None, str | None]:
        if HTTPMethod(method) != HTTPMethod.GET:  # don't store any response that is not from  GET request
            return None, None

        url = URL(url)  # e.g. https://api.spotify.com/v1/tracks/6fWoFduMpBem73DMLCOh1Z
        path_parts = url.path.strip("/").split("/")  # '<version>', '<name>', '<id>', ...
        if len(path_parts) < 3:
            return None, None

        return path_parts[2], path_parts[0]

    def get_name(self, payload: dict[str, Any]) -> str | None:
        if payload.get("type") == "user":
            return payload["display_name"]
        return payload.get("name")


# END
# REPOSITORY - INIT

from datetime import timedelta

from aiorequestful.cache.backend.base import ResponseRepository
from aiorequestful.response.payload import JSONPayloadHandler

settings = SpotifyRepositorySettings(name="tracks", payload_handler=JSONPayloadHandler())
repository = ResponseRepository(settings=settings, expire=timedelta(weeks=2))


# END
# REPOSITORY - USAGE

async def process_response(rep: ResponseRepository, req: tuple, payload: dict[str, Any]) -> None:
    await rep.create()  # create the repository in the cache backend
    await rep  # does the same as above

    await rep.save_response(response=(req, payload))  # store the payload in the cache

    assert await rep.get_response(request=req) == payload  # retrieve the cached payload
    assert rep.get_key_from_request(payload) == req  # get the key from a payload
    assert await rep.count(True) == 1  # the number of responses cached, including expired responses
    assert await rep.count(False) == 1  # the number of responses cached, excluding expired responses
    assert await rep.contains(req)  # check the key is in the repository

    await rep.delete_response(request=req)  # delete the response
    await rep.clear()  # OR clear all responses
    await rep.clear(True)  # OR clear only expired responses


async def process_request(rep: ResponseRepository) -> None:
    request = ("6fWoFduMpBem73DMLCOh1Z", "v1")
    payload = {"name": "super cool song"}
    await process_response(rep=rep, req=request, payload=payload)

# END
# CACHE - INIT

from aiorequestful.cache.backend import ResponseCache


def repository_getter(cache: ResponseCache, url: str | URL) -> ResponseRepository:
    path = URL(url).path
    path_split = [part.replace("-", "_") for part in path.split("/")[2:]]

    if len(path_split) < 3:
        name = path_split[0]
    else:
        name = "_".join([path_split[0].rstrip("s"), path_split[2].rstrip("s") + "s"])

    return cache.get(name)


response_cache = ResponseCache(
    cache_name="cache", repository_getter=repository_getter, expire=timedelta(weeks=2)
)

# or we can call the 'create' class method to simplify cache creation
response_cache = ResponseCache.create(value="db")

# END
# CACHE - SETUP

from aiohttp import ClientRequest, ClientResponse


async def setup_cache(cache: ResponseCache) -> None:
    payload_handler = JSONPayloadHandler()

    cache.create_repository(SpotifyRepositorySettings(name="tracks", payload_handler=payload_handler))
    cache.create_repository(SpotifyRepositorySettings(name="albums", payload_handler=payload_handler))
    cache.create_repository(SpotifyRepositorySettings(name="artists", payload_handler=payload_handler))


# END
# CACHE - USAGE

async def process_response(cache: ResponseCache, request: ClientRequest, response: ClientResponse) -> None:
    async with cache:  # connect and set up the repositories on the backed
        await cache.save_response(response=response)  # store the payload in the cache
        assert await cache.get_response(request=request) == await response.json()  # retrieve the cached payload
        await cache.delete_response(request=request)  # delete the response

# END
