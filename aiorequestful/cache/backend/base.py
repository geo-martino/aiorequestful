"""
Base interface for implementations of all cache backends.
"""
import asyncio
import logging
from abc import ABCMeta, abstractmethod
from collections.abc import MutableMapping, Callable, Collection, AsyncIterable, Mapping, Generator
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Self, Unpack

from aiohttp import RequestInfo, ClientRequest, ClientResponse
from dateutil.relativedelta import relativedelta

from aiorequestful._utils import get_iterator
from aiorequestful.cache.exception import CacheError
from aiorequestful.response.exception import PayloadHandlerError
from aiorequestful.response.payload import PayloadHandler, StringPayloadHandler
from aiorequestful.types import UnitCollection, URLInput, RequestKwargs

type CacheRequestType = RequestInfo | ClientRequest | ClientResponse
type RepositoryRequestType[K] = K | CacheRequestType

DEFAULT_EXPIRE: timedelta = timedelta(weeks=1)


@dataclass
class ResponseRepositorySettings[V](metaclass=ABCMeta):
    """Settings for a response type from a given endpoint to be used to configure a repository in the cache backend."""
    #: That name of the repository in the backend
    name: str
    #: Handles payload data conversion to/from expected format for de/serialization.
    payload_handler: PayloadHandler[V] = field(default=StringPayloadHandler())

    @property
    @abstractmethod
    def fields(self) -> tuple[str, ...]:
        """
        The names of the fields relating to the keys extracted by :py:meth:`get_key` in the order
        in which they appear from the results of this method.
        """
        raise NotImplementedError

    @abstractmethod
    def get_key(self, **kwargs: Unpack[RequestKwargs]) -> tuple:
        """
        Extracts the name to assign to a cache entry in the repository from the given request kwargs.

        Arguments passed through to `.aiohttp.ClientSession.request`.
        See aiohttp reference for more info on available kwargs:
        https://docs.aiohttp.org/en/stable/client_reference.html#aiohttp.ClientSession.request
        """
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    def get_name(payload: V) -> str | None:
        """Extracts the name to assign to a cache entry in the repository from a given ``response``."""
        raise NotImplementedError


class ResponseRepository[K: tuple, V: Any](AsyncIterable[tuple[K, V]], metaclass=ABCMeta):
    """
    Represents a repository in the backend cache, providing a dict-like interface
    for interacting with this repository.

    A repository is a data store within the backend e.g. a table in a database.

    :param settings: The settings to use to identify and interact with the repository in the backend.
    :param expire: The expiry time to apply to cached responses after which responses are invalidated.
    """

    __slots__ = ("logger", "connection", "settings", "_expire")

    # noinspection PyPropertyDefinition,PyMethodParameters
    @property
    @abstractmethod
    def _required_modules(cls) -> list:
        """The modules required to instantiate this repository"""
        return []

    @property
    def expire(self) -> datetime:
        """The datetime representing the maximum allowed expiry time from now."""
        return datetime.now() + self._expire

    @classmethod
    @abstractmethod
    def create(cls, *args, **kwargs) -> Self:
        """
        Set up the backend repository in the backend database if it doesn't already exist
        and return the initialised object that represents it.
        """
        raise NotImplementedError

    def __init__(self, settings: ResponseRepositorySettings[V], expire: timedelta | relativedelta = DEFAULT_EXPIRE):
        #: The :py:class:`logging.Logger` for this  object
        self.logger: logging.Logger = logging.getLogger(__name__)

        #: The settings to use to identify and interact with the repository in the backend.
        self.settings = settings
        self._expire = expire

        #: The current connection to the backend.
        self.connection = None

    @abstractmethod
    def __await__(self) -> Generator[None, None, Self]:
        raise NotImplementedError

    def __hash__(self):
        return hash(self.settings.name)

    @abstractmethod
    async def commit(self) -> None:
        """Commit the changes to the repository"""
        raise NotImplementedError

    @abstractmethod
    async def close(self) -> None:
        """Close the connection to the repository."""
        raise NotImplementedError

    @abstractmethod
    async def count(self, include_expired: bool = True) -> int:
        """
        Get the number of responses in this repository.

        :param include_expired: Whether to include expired responses in the final count.
        :return: The number of responses in this repository.
        """
        raise NotImplementedError

    @abstractmethod
    async def contains(self, request: RepositoryRequestType[K]) -> bool:
        """Check whether the repository contains a given ``request``"""
        raise NotImplementedError

    @abstractmethod
    async def clear(self, expired_only: bool = False) -> int:
        """
        Clear the repository of all entries.

        :param expired_only: Whether to only remove responses that have expired.
        :return: The number of responses cleared from the repository.
        """
        raise NotImplementedError

    async def serialize(self, value: Any) -> V | None:
        """
        Serialize a given ``value`` to a type that can be persisted to the repository.

        :return: Serialized object if serializing is possible, None otherwise.
        """
        if value is None:
            return

        try:
            return await self.settings.payload_handler.serialize(value)
        except PayloadHandlerError:
            return

    async def deserialize(self, value: V | None) -> Any:
        """
        Deserialize a value from the repository to the expected response value type.

        :return: Deserialized object if deserializing is possible, None otherwise.
        """
        if value is None:
            return

        try:
            return await self.settings.payload_handler.deserialize(value)
        except PayloadHandlerError:
            return

    @abstractmethod
    def get_key_from_request(self, request: RepositoryRequestType[K]) -> K:
        """Extract the key to use when persisting responses for a given ``request``"""
        raise NotImplementedError

    @abstractmethod
    async def get_response(self, request: RepositoryRequestType[K]) -> V | None:
        """
        Get the response relating to the given ``request`` from this repository if it exists.

        :return: The result if found.
        """
        raise NotImplementedError

    async def get_responses(self, requests: Collection[RepositoryRequestType[K]]) -> list[V]:
        """
        Get the responses relating to the given ``requests`` from this repository if they exist.

        :return: Results unordered.
        """
        tasks = asyncio.gather(*map(self.get_response, requests))
        return list(filter(lambda result: result is not None, await tasks))

    async def save_response(self, response: Collection[K, V] | ClientResponse) -> None:
        """Save the given ``response`` to this repository if a key can be extracted from it. Safely fail if not"""
        if isinstance(response, Collection):
            key, value = response
        else:
            key = self.get_key_from_request(response)
            if not key:
                return

            value: V = await self.deserialize(response)

        await self._set_item_from_key_value_pair(key, await self.serialize(value))

    @abstractmethod
    async def _set_item_from_key_value_pair(self, __key: K, __value: Any) -> None:
        raise NotImplementedError

    async def save_responses(self, responses: Mapping[K, V] | Collection[ClientResponse]) -> None:
        """
        Save the given ``responses`` to this repository if a key can be extracted from them.
        Safely fail on those that can't.
        """
        if isinstance(responses, Mapping):
            tasks = [
                self._set_item_from_key_value_pair(key, await self.serialize(value))
                for key, value in responses.items()
            ]
        else:
            tasks = map(self.save_response, responses)

        await asyncio.gather(*tasks)

    @abstractmethod
    async def delete_response(self, request: RepositoryRequestType[K]) -> bool:
        """
        Delete the given ``request`` from this repository if it exists.

        :return: True if deleted in the repository and False if ``request`` was not found in the repository.
        """
        raise NotImplementedError

    async def delete_responses(self, requests: Collection[RepositoryRequestType[K]]) -> int:
        """
        Delete the given ``requests`` from this repository if they exist.

        :return: The number of the given ``requests`` deleted in the repository.
        """
        tasks = asyncio.gather(*map(self.delete_response, requests))
        return sum(await tasks)


class ResponseCache[R: ResponseRepository](MutableMapping[str, R], metaclass=ABCMeta):
    """
    Represents a backend cache of many repositories, providing a dict-like interface for interacting with them.

    :param cache_name: The name to give to this cache.
    :param repository_getter: A function that can be used to identify the repository in this cache
        that matches a given URL.
    :param expire: The expiry time to apply to cached responses after which responses are invalidated.
    """

    __slots__ = ("cache_name", "repository_getter", "expire", "_repositories")

    # noinspection PyPropertyDefinition
    @classmethod
    @property
    @abstractmethod
    def type(cls) -> str:
        """A string representing the type of the backend this class represents."""
        # raise NotImplementedError - omitted here as it causes docs build to fail

    @classmethod
    @abstractmethod
    async def connect(cls, value: Any, **kwargs) -> Self:
        """Connect to the backend from a given generic ``value``."""
        raise NotImplementedError

    def __init__(
            self,
            cache_name: str,
            repository_getter: Callable[[Self, URLInput], R | None] = None,
            expire: timedelta | relativedelta = DEFAULT_EXPIRE,
    ):
        super().__init__()

        #: The name to give to this cache.
        self.cache_name = cache_name
        #: A function that can be used to identify the repository in this cache that matches a given URL.
        self.repository_getter = repository_getter
        #: The expiry time to apply to cached responses after which responses are invalidated.
        self.expire = expire

        self._repositories: dict[str, R] = {}

    @abstractmethod
    def __await__(self) -> Generator[None, None, Self]:
        raise NotImplementedError

    async def __aenter__(self) -> Self:
        return await self

    @abstractmethod
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        raise NotImplementedError

    def __repr__(self):
        return repr(self._repositories)

    def __str__(self):
        return str(self._repositories)

    def __iter__(self):
        return iter(self._repositories)

    def __len__(self):
        return len(self._repositories)

    def __getitem__(self, item):
        return self._repositories[item]

    def __setitem__(self, key, value):
        self._repositories[key] = value

    def __delitem__(self, key):
        del self._repositories[key]

    @abstractmethod
    async def commit(self) -> None:
        """Commit the changes to the cache"""
        raise NotImplementedError

    @abstractmethod
    async def close(self):
        """Close the connection to the repository."""
        raise NotImplementedError

    @abstractmethod
    def create_repository(self, settings: ResponseRepositorySettings) -> ResponseRepository:
        """
        Create and return a :py:class:`SQLiteResponseStorage` and store this object in this cache.

        Creates a repository with the given ``settings`` in the cache if it doesn't exist.
        """
        raise NotImplementedError

    def get_repository_from_url(self, url: URLInput) -> R | None:
        """Returns the repository to use from the stored repositories in this cache for the given ``url``."""
        if self.repository_getter is not None:
            return self.repository_getter(self, url)

    def get_repository_from_requests(self, requests: UnitCollection[CacheRequestType]) -> R | None:
        """Returns the repository to use from the stored repositories in this cache for the given ``requests``."""
        requests = get_iterator(requests)
        results = {self.get_repository_from_url(request.url) for request in requests}
        if len(results) > 1:
            raise CacheError(
                "Too many different types of requests given. Given requests must relate to the same repository type"
            )
        return next(iter(results), None)

    async def get_response(self, request: CacheRequestType) -> Any:
        """
        Get the response relating to the given ``request`` from the appropriate repository if it exists.

        :return: The result if found.
        """
        repository = self.get_repository_from_requests([request])
        if repository is not None:
            return await repository.get_response(request)

    async def get_responses(self, requests: Collection[CacheRequestType]) -> list:
        """
        Get the responses relating to the given ``requests`` from the appropriate repository if they exist.

        :return: Results unordered.
        """
        repository = self.get_repository_from_requests(requests)
        if repository is not None:
            return await repository.get_responses(requests)

    async def save_response(self, response: ClientResponse) -> None:
        """Save the given ``response`` to the appropriate repository if a key can be extracted from it."""
        repository = self.get_repository_from_requests([response])
        if repository is not None:
            return await repository.save_response(response)

    async def save_responses(self, responses: Collection[ClientResponse]) -> None:
        """
        Save the given ``responses`` to the appropriate repository if a key can be extracted from them.
        Safely fail on those that can't.
        """
        repository = self.get_repository_from_requests(responses)
        if repository is not None:
            return await repository.save_responses(responses)

    async def delete_response(self, request: CacheRequestType) -> bool:
        """
        Delete the given ``request`` from the appropriate repository if it exists.

        :return: True if deleted in the repository and False if ``request`` was not found in the repository.
        """
        repository = self.get_repository_from_requests([request])
        if repository is not None:
            return await repository.delete_response(request)

    async def delete_responses(self, requests: Collection[CacheRequestType]) -> int:
        """
        Delete the given ``requests`` from the appropriate repository.

        :return: The number of the given ``requests`` deleted in the repository.
        """
        repository = self.get_repository_from_requests(requests)
        if repository is not None:
            return await repository.delete_responses(requests)
