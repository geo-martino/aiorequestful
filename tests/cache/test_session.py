from random import choice
from typing import Any

import pytest
from aioresponses import aioresponses
from faker import Faker

from aiorequestful.cache.backend.base import ResponseCache
from aiorequestful.cache.session import CachedSession
from aiorequestful.response.payload import PayloadHandler, JSONPayloadHandler, StringPayloadHandler
from tests.cache.backend.test_sqlite import TestSQLiteCache as SQLiteCacheTester
from tests.cache.backend.testers import ResponseCacheTester
from tests.cache.backend.utils import MockResponseRepositorySettings
from tests.utils import idfn

fake = Faker()


class TestCachedSession:

    @pytest.fixture(scope="class", params=[StringPayloadHandler(), JSONPayloadHandler(indent=2)], ids=idfn)
    def payload_handler(self, request) -> PayloadHandler:
        """Yields the :py:class:`PayloadHandler` to apply to the :py:class:`RequestSettings`"""
        return request.param

    @pytest.fixture(scope="class", params=[SQLiteCacheTester], ids=idfn)
    def tester(self, request) -> ResponseCacheTester:
        return request.param

    @pytest.fixture
    def connection(self, tester: ResponseCacheTester) -> Any:
        """Yields a valid :py:class:`Connection` to use throughout tests in this suite as a pytest.fixture."""
        return tester.generate_connection()

    # noinspection PyTestUnpassedFixture
    @pytest.fixture
    async def cache(self, tester: ResponseCacheTester, payload_handler: PayloadHandler) -> ResponseCache:
        """Yields a valid :py:class:`ResponseCache` to use throughout tests in this suite as a pytest.fixture."""
        async with tester.generate_cache(payload_handler=payload_handler) as cache:
            yield cache

    @pytest.fixture
    async def session(self, cache: ResponseCache) -> CachedSession:
        """
        Yields a valid :py:class:`CachedSession` with the given ``cache``
        to use throughout tests in this suite as a pytest.fixture.
        """
        async with CachedSession(cache=cache) as session:
            yield session

    async def test_context_management(self, cache: ResponseCache):
        # does not create repository backend resource until entered
        settings = MockResponseRepositorySettings(name=fake.word())
        session = CachedSession(cache=cache)
        repository = cache.create_repository(settings)

        with pytest.raises(Exception):
            await repository.count()
        async with session:
            await repository.count()

    async def test_request_cached(
            self,
            session: CachedSession,
            cache: ResponseCache,
            tester: ResponseCacheTester,
            requests_mock: aioresponses
    ):
        repository = choice(list(cache.values()))

        key, value = choice([(k, v) async for k, v in repository])
        assert await repository.contains(key)

        expected = await tester.generate_response_from_item(repository.settings, key, value, session=session)
        request = expected.request_info

        async with session.request(method=request.method, url=request.url) as response:
            assert await response.text() == await expected.text()
        requests_mock.assert_not_called()

    async def test_repeated_request(
            self,
            session: CachedSession,
            cache: ResponseCache,
            tester: ResponseCacheTester,
            requests_mock: aioresponses,
    ):
        repository = choice(list(cache.values()))

        expected = await tester.generate_response(repository.settings, session=session)
        request = expected.request_info

        key = repository.get_key_from_request(request)
        assert not await repository.contains(key)

        requests_mock.get(request.url, body=await expected.text(), repeat=True)

        async with session.request(method=request.method, url=request.url, persist=False) as response:
            assert await response.text() == await expected.text()
        assert len(requests_mock.requests) == 1
        assert sum(map(len, requests_mock.requests.values())) == 1
        assert not await repository.contains(key)

        async with session.request(method=request.method, url=request.url, persist=True) as response:
            assert await response.text() == await expected.text()
        assert len(requests_mock.requests) == 1
        assert sum(map(len, requests_mock.requests.values())) == 2
        assert await repository.contains(key)

        async with session.request(method=request.method, url=request.url) as response:
            assert await response.text() == await expected.text()
        assert len(requests_mock.requests) == 1
        assert sum(map(len, requests_mock.requests.values())) == 2

    async def test_bad_response_not_cached(
            self,
            session: CachedSession,
            cache: ResponseCache,
            tester: ResponseCacheTester,
            requests_mock: aioresponses,
    ):
        repository = choice(list(cache.values()))

        expected = await tester.generate_response(repository.settings, session=session)
        request = expected.request_info

        key = repository.get_key_from_request(request)
        assert not await repository.contains(key)

        requests_mock.get(request.url, status=404, body=await expected.text())
        async with session.request(method=request.method, url=request.url, persist=True) as response:
            assert await response.text() == await expected.text()

        assert len(requests_mock.requests) == 1
        assert sum(map(len, requests_mock.requests.values())) == 1
        assert not await repository.contains(key)

        requests_mock.get(request.url, status=200, body=await expected.text())
        async with session.request(method=request.method, url=request.url, persist=True) as response:
            assert await response.text() == await expected.text()

        assert len(requests_mock.requests) == 1
        assert sum(map(len, requests_mock.requests.values())) == 2
        assert await repository.contains(key)
