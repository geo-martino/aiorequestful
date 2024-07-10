import contextlib
import sqlite3
from collections.abc import Iterable
from datetime import datetime, timedelta
from pathlib import Path
from random import randrange
from tempfile import gettempdir
from typing import Any

import aiosqlite
import pytest
from aiohttp import ClientRequest, ClientResponse, ClientSession
from faker import Faker
from yarl import URL

from aiorequestful.cache.backend.base import ResponseRepositorySettings
from aiorequestful.cache.backend.sqlite import SQLiteTable, SQLiteCache
from aiorequestful.cache.response import CachedResponse
from aiorequestful.response.payload import PayloadHandler
from tests.cache.backend.testers import ResponseRepositoryTester, ResponseCacheTester, BaseResponseTester
from tests.cache.backend.utils import MockPaginatedRequestSettings

fake = Faker()


class SQLiteTester(BaseResponseTester):
    """Supplies common functionality expected of all SQLite test suites."""

    @staticmethod
    def generate_connection() -> sqlite3.Connection:
        return aiosqlite.connect(":memory:")

    @staticmethod
    async def generate_item[V: Any](settings: ResponseRepositorySettings[V]) -> tuple[tuple[Any, ...], V]:
        key = ("GET", "".join(fake.random_letters(20)),)

        value = {
            fake.word(): fake.word(),
            fake.word(): fake.word(),
            str(randrange(0, 100)): fake.word(),
            str(randrange(0, 100)): randrange(0, 100),
        }

        if isinstance(settings, MockPaginatedRequestSettings):
            key = (*key, randrange(0, 100), randrange(1, 50))

        return key, await settings.payload_handler.deserialize(value)

    @classmethod
    async def generate_response_from_item[V: Any](
            cls, settings: ResponseRepositorySettings[V], key: Any, value: V, session: ClientSession = None
    ) -> ClientResponse:
        url = f"http://test.com/{settings.name}/{key[1]}"
        return await cls._generate_response_from_item(
            url=url, key=key, value=value, payload_handler=settings.payload_handler, session=session
        )

    @classmethod
    async def generate_bad_response_from_item[V: Any](
            cls, settings: ResponseRepositorySettings[V], key: Any, value: V, session: ClientSession = None
    ) -> ClientResponse:
        url = "http://test.com"
        return await cls._generate_response_from_item(
            url=url, key=key, value=value, payload_handler=settings.payload_handler, session=session
        )

    @staticmethod
    async def _generate_response_from_item(
            url: str, key: Any, value: Any, payload_handler: PayloadHandler, session: ClientSession = None
    ) -> ClientResponse:
        params = {}
        if len(key) == 4:
            params["offset"] = key[2]
            params["limit"] = key[3]

        if session is not None:
            # noinspection PyProtectedMember
            request = ClientRequest(
                method=key[0],
                url=URL(url),
                params=params,
                loop=session._loop,
                session=session
            )
        else:
            request = ClientRequest(
                method=key[0],
                url=URL(url),
                params=params,
            )
        return CachedResponse(request=request, payload=await payload_handler.serialize(value))


class TestSQLiteTable(SQLiteTester, ResponseRepositoryTester):

    @pytest.fixture
    async def repository[V: str](
            self,
            connection: aiosqlite.Connection,
            settings: ResponseRepositorySettings[V],
            valid_items: dict[Iterable[Any], V],
            invalid_items: dict[Iterable[Any], V],
    ) -> SQLiteTable:
        expire = timedelta(days=2)

        async with connection:
            repository = await SQLiteTable(connection, settings=settings, expire=expire)

            columns = (
                *repository._primary_key_columns,
                repository.cached_column,
                repository.expiry_column,
                repository.payload_column
            )
            query = "\n".join((
                f"INSERT OR REPLACE INTO {settings.name} (",
                f"\t{", ".join(columns)}",
                ") ",
                f"VALUES ({",".join("?" * len(columns))});",
            ))
            parameters = [
                (*key, datetime.now().isoformat(), repository.expire.isoformat(), await repository.serialize(value))
                for key, value in valid_items.items()
            ]
            invalid_expire_dt = datetime.now() - expire  # expiry time in the past, response cache has expired
            parameters += [
                (*key, datetime.now().isoformat(), invalid_expire_dt.isoformat(), await repository.serialize(value))
                for key, value in invalid_items.items()
            ]

            await connection.executemany(query, parameters)
            await repository.commit()

            yield repository

    async def test_init_fails(self, connection: aiosqlite.Connection, settings: ResponseRepositorySettings):
        repository = SQLiteTable(connection, settings=settings)
        with pytest.raises(ValueError):
            assert await repository.count()

        with pytest.raises(ValueError):
            await repository

        async with connection:
            async with connection.execute(
                    f"SELECT name FROM sqlite_master WHERE type='table' AND name='{settings.name}'"
            ) as cur:
                rows = await cur.fetchall()
        assert len(rows) == 0

    async def test_init(self, connection: aiosqlite.Connection, settings: ResponseRepositorySettings):
        async with connection:
            repository = await SQLiteTable(connection, settings=settings)

            async with connection.execute(
                    f"SELECT name FROM sqlite_master WHERE type='table' AND name='{settings.name}'"
            ) as cur:
                rows = await cur.fetchall()
            assert len(rows) == 1
            assert rows[0][0] == settings.name

            async with connection.execute(f"SELECT name FROM pragma_table_info('{settings.name}');") as cur:
                columns = {row[0] async for row in cur}
            assert {repository.name_column, repository.payload_column, repository.expiry_column}.issubset(columns)
            assert set(repository._primary_key_columns).issubset(columns)

            assert await repository.count() == 0

        with pytest.raises(ValueError):
            assert await repository.count()


class TestSQLiteCache(SQLiteTester, ResponseCacheTester):

    @staticmethod
    async def generate_response(settings: ResponseRepositorySettings, session: ClientSession = None) -> ClientResponse:
        key, value = await TestSQLiteTable.generate_item(settings)
        return await TestSQLiteTable.generate_response_from_item(settings, key, value, session=session)

    @classmethod
    @contextlib.asynccontextmanager
    async def generate_cache(cls, payload_handler: PayloadHandler) -> SQLiteCache:
        async with SQLiteCache(
                cache_name="test",
                connector=cls.generate_connection,
                repository_getter=cls.get_repository_from_url,
        ) as cache:
            for _ in range(randrange(5, 10)):
                settings = cls.generate_settings(payload_handler=payload_handler)
                items = dict([await TestSQLiteTable.generate_item(settings) for _ in range(randrange(3, 6))])

                repository = await SQLiteTable(settings=settings, connection=cache.connection)
                for k, v in items.items():
                    await repository._set_item_from_key_value_pair(k, await repository.serialize(v))
                cache[settings.name] = repository

            await cache.commit()
            assert await repository.count() == len(items)

            yield cache

    @staticmethod
    def get_repository_from_url(cache: SQLiteCache, url: str | URL) -> SQLiteTable | None:
        url = URL(url)
        for name, repository in cache.items():
            if name == url.path.split("/")[-2]:
                return repository

    @staticmethod
    async def get_db_path(cache: SQLiteCache) -> str:
        """Get the DB path from the connection associated with the given ``cache``."""
        async with cache.connection.execute("PRAGMA database_list") as cur:
            rows = await cur.fetchall()

        assert len(rows) == 1
        db_seq, db_name, db_path = rows[0]
        return db_path

    async def test_connect_with_path(self, tmp_path: Path):
        fake_name = "not my real name"
        path = tmp_path.joinpath("test")
        expire = timedelta(weeks=42)

        async with SQLiteCache.connect_with_path(path, cache_name=fake_name, expire=expire) as cache:
            assert await self.get_db_path(cache) == str(path.with_suffix(".sqlite"))
            assert cache.cache_name != fake_name
            assert cache.expire == expire

    async def test_connect_with_in_memory_db(self):
        fake_name = "not my real name"
        expire = timedelta(weeks=42)

        async with SQLiteCache.connect_with_in_memory_db(cache_name=fake_name, expire=expire) as cache:
            assert await self.get_db_path(cache) == ""
            assert cache.cache_name != fake_name
            assert cache.expire == expire

    async def test_connect_with_temp_db(self):
        name = "this is my real name"
        path = Path(gettempdir(), name)
        expire = timedelta(weeks=42)

        async with SQLiteCache.connect_with_temp_db(name, expire=expire) as cache:
            assert (await self.get_db_path(cache)).endswith(str(path.with_suffix(".sqlite")))
            assert cache.cache_name == name
            assert cache.expire == expire
