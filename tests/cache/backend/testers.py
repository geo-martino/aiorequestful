import sqlite3
from abc import ABCMeta, abstractmethod
from collections.abc import Iterable
from random import choice, randrange
from typing import Any

import pytest
from aiohttp import ClientResponse, ClientSession
from faker import Faker

from aiorequestful.cache.backend.base import ResponseRepository, ResponseCache, ResponseRepositorySettings
from aiorequestful.cache.exception import CacheError
from aiorequestful.response.payload import PayloadHandler, StringPayloadHandler, JSONPayloadHandler
from tests.cache.backend.utils import MockResponseRepositorySettings, MockPaginatedRequestSettings
from tests.utils import ParamTester, idfn

fake = Faker()

REQUEST_SETTINGS = [
    MockResponseRepositorySettings,
    MockPaginatedRequestSettings,
]


class BaseResponseTester(ParamTester, metaclass=ABCMeta):
    """Base functionality for all test suites related to the ``cache`` package."""

    @pytest.fixture(scope="class", params=[StringPayloadHandler(), JSONPayloadHandler(indent=2)], ids=idfn)
    def payload_handler(self, request) -> PayloadHandler:
        """Yields the :py:class:`PayloadHandler` to apply to the :py:class:`RequestSettings`"""
        return request.param

    @staticmethod
    @abstractmethod
    def generate_connection() -> Any:
        """Generates and yields a :py:class:`Connection` for this backend type."""
        raise NotImplementedError

    @pytest.fixture
    def connection(self) -> Any:
        """Yields a valid :py:class:`Connection` to use throughout tests in this suite as a pytest_asyncio.fixture."""
        return self.generate_connection()

    @staticmethod
    @abstractmethod
    async def generate_item[V: Any](settings: ResponseRepositorySettings[V]) -> tuple[Iterable[Any], V]:
        """
        Randomly generates an item (key, value) appropriate for the given ``settings``
        that can be persisted to the repository.
        """
        raise NotImplementedError

    @classmethod
    @abstractmethod
    async def generate_response_from_item[V: Any](
            cls, settings: ResponseRepositorySettings[V], key: Any, value: V, session: ClientSession = None
    ) -> ClientResponse:
        """
        Generates a :py:class:`ClientResponse` appropriate for the given ``settings``
        from the given ``key`` and ``value`` that can be persisted to the repository.
        """
        raise NotImplementedError

    @classmethod
    @abstractmethod
    async def generate_bad_response_from_item[V: Any](
            cls, settings: ResponseRepositorySettings[V], key: Any, value: V, session: ClientSession = None
    ) -> ClientResponse:
        """
        Generates a bad :py:class:`ClientResponse` appropriate for the given ``settings``
        from the given ``key`` and ``value`` that can be persisted to the repository.
        """
        raise NotImplementedError


class ResponseRepositoryTester(BaseResponseTester, metaclass=ABCMeta):
    """Run generic tests for :py:class:`ResponseRepository` implementations."""

    # noinspection PyArgumentList
    @pytest.fixture(scope="class", params=REQUEST_SETTINGS)
    def settings(self, request, payload_handler: PayloadHandler) -> ResponseRepositorySettings:
        """
        Yields the :py:class:`RequestSettings` to use when creating a new :py:class:`ResponseRepository`
        as a pytest.fixture.
        """
        cls: type[ResponseRepositorySettings] = request.param
        return cls(name="test", payload_handler=payload_handler)

    @pytest.fixture(scope="class")
    async def valid_items[V: Any](self, settings: ResponseRepositorySettings[V]) -> dict[Iterable[Any], V]:
        """Yields expected items to be found in the repository that have not expired as a pytest.fixture."""
        return dict([await self.generate_item(settings) for _ in range(randrange(3, 6))])

    @pytest.fixture(scope="class")
    async def invalid_items[V: Any](self, settings: ResponseRepositorySettings[V]) -> dict[Iterable[Any], V]:
        """Yields expected items to be found in the repository that have passed the expiry time as a pytest.fixture."""
        return dict([await self.generate_item(settings) for _ in range(randrange(3, 6))])

    @pytest.fixture(scope="class")
    def items[V: Any](
            self, valid_items: dict[Iterable[Any], V], invalid_items: dict[Iterable[Any], V]
    ) -> dict[Iterable[Any], V]:
        """Yields all expected items to be found in the repository as a pytest.fixture."""
        return valid_items | invalid_items

    @abstractmethod
    async def repository[V: Any](
            self,
            connection: Any,
            settings: ResponseRepositorySettings[V],
            valid_items: dict[Iterable[Any], V],
            invalid_items: dict[Iterable[Any], V],
    ) -> ResponseRepository:
        """
        Yields a valid :py:class:`ResponseRepository` to use throughout tests in this suite as a pytest_asyncio.fixture.
        Populates this repository with ``valid_items`` and ``invalid_items``.
        """
        raise NotImplementedError

    @staticmethod
    async def test_close(repository: ResponseRepository):
        key, _ = await anext(aiter(repository))
        await repository.close()

        with pytest.raises(ValueError):
            await repository.get_response(key)

    @staticmethod
    async def test_count(repository: ResponseRepository, items: dict, valid_items: dict):
        assert await repository.count() == len(items)
        assert await repository.count(False) == len(valid_items)

    @staticmethod
    async def test_contains_and_clear(repository: ResponseRepository):
        key, _ = await anext(aiter(repository))
        assert await repository.count() > 0
        assert await repository.contains(key)

        await repository.clear()
        assert await repository.count() == 0
        assert not await repository.contains(key)

    async def test_serialize(self, repository: ResponseRepository):
        _, value = await self.generate_item(repository.settings)
        value_serialized = await repository.serialize(value)

        assert await repository.serialize(value_serialized) == value_serialized

        assert await repository.serialize(None) is None

    # noinspection PyTypeChecker
    async def test_deserialize(self, repository: ResponseRepository):
        _, value = await self.generate_item(repository.settings)
        value_str = await repository.serialize(value)
        value_deserialized = await repository.deserialize(value_str)

        assert await repository.deserialize(value_deserialized) == value

        assert await repository.deserialize(None) is None

    async def test_get_key_from_request(self, repository: ResponseRepository):
        key, value = await self.generate_item(repository.settings)
        request = (await self.generate_response_from_item(repository.settings, key, value)).request_info
        assert repository.get_key_from_request(request) == key

    async def test_get_key_from_invalid_request(self, repository: ResponseRepository):
        key, value = await self.generate_item(repository.settings)
        request = (await self.generate_bad_response_from_item(repository.settings, key, value)).request_info
        assert repository.get_key_from_request(request) is None

    @staticmethod
    async def test_get_responses_from_keys(repository: ResponseRepository, valid_items: dict):
        key, value = choice(list(valid_items.items()))
        assert await repository.get_response(key) == await repository.deserialize(value)
        assert await repository.get_responses(valid_items.keys()) == [
            await repository.deserialize(v) for v in valid_items.values()
        ]

    async def test_get_response_on_missing(self, repository: ResponseRepository, valid_items: dict):
        key, value = await self.generate_item(repository.settings)
        assert not await repository.contains(key)

        assert await repository.get_response(key) is None
        assert await repository.get_responses(list(valid_items) + [key]) == list(valid_items.values())

    async def test_get_responses_from_requests(self, repository: ResponseRepository, valid_items: dict):
        key, value = choice(list(valid_items.items()))
        request = (await self.generate_response_from_item(repository.settings, key, value)).request_info
        assert await repository.get_response(request) == value

        requests = [
            (await self.generate_response_from_item(repository.settings, key, value)).request_info
            for key, value in valid_items.items()
        ]
        assert await repository.get_responses(requests) == list(valid_items.values())

    async def test_get_response_from_responses(self, repository: ResponseRepository, valid_items: dict):
        key, value = choice(list(valid_items.items()))
        response = await self.generate_response_from_item(repository.settings, key, value)
        assert await repository.get_response(response) == value

        responses = [
            await self.generate_response_from_item(repository.settings, key, value)
            for key, value in valid_items.items()
        ]
        assert await repository.get_responses(responses) == list(valid_items.values())

    async def test_get_response_from_responses_on_missing(self, repository: ResponseRepository, valid_items: dict):
        key, value = choice(list(valid_items.items()))
        response = await self.generate_bad_response_from_item(repository.settings, key, value)
        assert await repository.get_response(response) is None

        responses = [
            await self.generate_bad_response_from_item(repository.settings, key, value)
            for key, value in valid_items.items()
        ]
        assert await repository.get_responses(responses) == []

    async def test_set_item_from_key_value_pair(self, repository: ResponseRepository):
        items = [await self.generate_item(repository.settings) for _ in range(randrange(3, 6))]
        assert all([not await repository.contains(key) for key, _ in items])

        for key, value in items:
            await repository._set_item_from_key_value_pair(key, value)

        assert all([await repository.contains(key) for key, _ in items])
        for key, value in items:
            assert await repository.get_response(key) == value

    async def test_save_response_from_collection(self, repository: ResponseRepository):
        key, value = await self.generate_item(repository.settings)
        assert not await repository.contains(key)

        await repository.save_response((key, value))
        assert await repository.contains(key)
        assert await repository.get_response(key) == value

    async def test_save_response_from_response(self, repository: ResponseRepository):
        key, value = await self.generate_item(repository.settings)
        response = await self.generate_response_from_item(repository.settings, key, value)
        assert not await repository.contains(key)

        await repository.save_response(response)
        assert await repository.contains(key)
        assert await repository.get_response(key) == value

    async def test_save_response_fails_silently(self, repository: ResponseRepository):
        key, value = await self.generate_item(repository.settings)
        assert not await repository.contains(key)

        response = await self.generate_bad_response_from_item(repository.settings, key, value)
        await repository.save_response(response)
        assert not await repository.contains(key)

    async def test_save_responses_from_mapping(self, repository: ResponseRepository):
        items = dict([await self.generate_item(repository.settings) for _ in range(randrange(3, 6))])
        assert all([not await repository.contains(key) for key in items])

        await repository.save_responses(items)
        assert all([await repository.contains(key) for key in items])
        for key, value in items.items():
            assert await repository.get_response(key) == value

    async def test_save_responses_from_responses(self, repository: ResponseRepository):
        items = dict([await self.generate_item(repository.settings) for _ in range(randrange(3, 6))])
        responses = [
            await self.generate_response_from_item(repository.settings, key, value)
            for key, value in items.items()
        ]
        assert all([not await repository.contains(key) for key in items])

        await repository.save_responses(responses)
        assert all([await repository.contains(key) for key in items])
        for key, value in items.items():
            assert await repository.get_response(key) == value

    async def test_save_responses_fails_silently(self, repository: ResponseRepository):
        items = dict([await self.generate_item(repository.settings) for _ in range(randrange(3, 6))])
        assert all([not await repository.contains(key) for key in items])

        responses = [
            await self.generate_bad_response_from_item(repository.settings, key, value)
            for key, value in items.items()
        ]
        await repository.save_responses(responses)
        assert all([not await repository.contains(key) for key in items])

    async def test_delete_response_on_missing(self, repository: ResponseRepository):
        key, value = await self.generate_item(repository.settings)
        assert not await repository.contains(key)
        assert not await repository.delete_response(key)

    @staticmethod
    async def test_delete_response_from_key(repository: ResponseRepository, valid_items: dict):
        key, value = choice(list(valid_items.items()))
        assert await repository.contains(key)

        assert await repository.delete_response(key)
        assert not await repository.contains(key)

    async def test_delete_response_from_request(self, repository: ResponseRepository, valid_items: dict):
        key, value = choice(list(valid_items.items()))
        request = (await self.generate_response_from_item(repository.settings, key, value)).request_info
        assert await repository.contains(key)

        assert await repository.delete_response(request)
        assert not await repository.contains(key)

    async def test_delete_responses_from_requests(self, repository: ResponseRepository, valid_items: dict):
        requests = [
            (await self.generate_response_from_item(repository.settings, key, value)).request_info
            for key, value in valid_items.items()
        ]
        for key in valid_items:
            assert await repository.contains(key)

        assert await repository.delete_responses(requests) == len(requests)
        for key in valid_items:
            assert not await repository.contains(key)

    async def test_delete_response_from_response(self, repository: ResponseRepository, valid_items: dict):
        key, value = choice(list(valid_items.items()))
        response = await self.generate_response_from_item(repository.settings, key, value)
        assert await repository.contains(key)

        assert await repository.delete_response(response)
        assert not await repository.contains(key)

    async def test_delete_responses_from_responses(self, repository: ResponseRepository, valid_items: dict):
        responses = [
            await self.generate_response_from_item(repository.settings, key, value)
            for key, value in valid_items.items()
        ]
        for key in valid_items:
            assert await repository.contains(key)

        assert await repository.delete_responses(responses) == len(responses)
        for key in valid_items:
            assert not await repository.contains(key)


class ResponseCacheTester(BaseResponseTester, metaclass=ABCMeta):
    """Run generic tests for :py:class:`ResponseCache` implementations."""

    # noinspection PyArgumentList
    @staticmethod
    def generate_settings(payload_handler: PayloadHandler) -> ResponseRepositorySettings:
        """Randomly generates a :py:class:`RequestSettings` object that can be used to create a repository."""
        cls: type[ResponseRepositorySettings] = choice(REQUEST_SETTINGS)
        return cls(name="".join(fake.random_letters(20)), payload_handler=payload_handler)

    @staticmethod
    @abstractmethod
    async def generate_response(settings: ResponseRepositorySettings, session: ClientSession = None) -> ClientResponse:
        """
        Randomly generates a :py:class:`ClientResponse` appropriate for the given ``settings``
        that can be persisted to the repository.
        """
        raise NotImplementedError

    @classmethod
    @abstractmethod
    async def generate_cache(cls, payload_handler: PayloadHandler) -> ResponseCache:
        """
        Generates a :py:class:`ResponseCache` for this backend type
        with many randomly generated :py:class:`ResponseRepository` objects assigned
        and a ``response_getter`` assigned to get these repositories.
        """
        raise NotImplementedError

    # noinspection PyTestUnpassedFixture
    @pytest.fixture
    async def cache(self, payload_handler: PayloadHandler) -> ResponseCache:
        """Yields a valid :py:class:`ResponseCache` to use throughout tests in this suite as a pytest.fixture."""
        async with self.generate_cache(payload_handler=payload_handler) as cache:
            yield cache

    @staticmethod
    @abstractmethod
    def get_repository_from_url(cache: ResponseCache, url: str) -> ResponseCache:
        """Returns a repository for the given ``url`` from the given ``cache``."""
        raise NotImplementedError

    @staticmethod
    async def test_init(cache: ResponseCache):
        assert cache.values()
        for repository in cache.values():
            assert await repository.count()

    async def test_context_management(self, cache: ResponseCache, payload_handler: PayloadHandler):
        # does not create repository backend resource until awaited or entered
        settings = self.generate_settings(payload_handler=payload_handler)
        while settings.name in cache:
            settings = self.generate_settings(payload_handler=payload_handler)

        repository = cache.create_repository(settings)

        with pytest.raises(sqlite3.OperationalError):
            await repository.count()
        await cache
        await repository.count()

        settings = self.generate_settings(payload_handler=payload_handler)
        while settings.name in cache:
            settings = self.generate_settings(payload_handler=payload_handler)

        repository = cache.create_repository(settings)

        with pytest.raises(sqlite3.OperationalError):
            await repository.count()
        async with cache:
            await repository.count()

    async def test_create_repository(self, cache: ResponseCache, payload_handler: PayloadHandler):
        settings = self.generate_settings(payload_handler=payload_handler)
        while settings.name in cache:
            settings = self.generate_settings(payload_handler=payload_handler)

        # noinspection PyAsyncCall
        cache.create_repository(settings)
        assert settings.name in cache
        assert cache[settings.name].settings == settings

        # does not create a repository that already exists
        repository = choice(list(cache.values()))
        with pytest.raises(CacheError):
            # noinspection PyAsyncCall
            cache.create_repository(repository.settings)

    async def test_get_repository_for_url(self, cache: ResponseCache):
        repository = choice(list(cache.values()))
        url = (await self.generate_response(repository.settings)).request_info.url

        assert cache.get_repository_from_url(url).settings.name == repository.settings.name
        assert cache.get_repository_from_url(f"http://www.does-not-exist.com/{fake.word()}/{fake.uuid4(str)}") is None
        cache.repository_getter = None
        assert cache.get_repository_from_url(url) is None

    async def test_get_repository_for_requests(self, cache: ResponseCache):
        repository = choice(list(cache.values()))
        requests = [(await self.generate_response(repository.settings)).request_info for _ in range(3, 6)]
        assert cache.get_repository_from_requests(requests) == repository

    async def test_get_repository_for_responses(self, cache: ResponseCache, payload_handler: PayloadHandler):
        repository = choice(list(cache.values()))
        responses = [await self.generate_response(repository.settings) for _ in range(3, 6)]
        assert cache.get_repository_from_requests(responses).settings.name == repository.settings.name

        new_settings = self.generate_settings(payload_handler=payload_handler)
        new_responses = [await self.generate_response(new_settings) for _ in range(3, 6)]
        assert cache.get_repository_from_requests(new_responses) is None

        with pytest.raises(CacheError):  # multiple types given
            assert cache.get_repository_from_requests(responses + new_responses)

        cache.repository_getter = None
        assert cache.get_repository_from_requests(responses) is None

    async def test_repository_operations(self, cache: ResponseCache):
        repository = choice(list(cache.values()))

        response = await self.generate_response(repository.settings)
        key = repository.get_key_from_request(response.request_info)
        await cache.save_response(response)
        assert await repository.contains(key)

        assert await cache.get_response(response) == await repository.deserialize(response)

        assert await cache.delete_response(response)
        assert not await repository.contains(key)
