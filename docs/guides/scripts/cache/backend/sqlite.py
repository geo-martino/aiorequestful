from docs.guides.scripts.cache.backend.base import SpotifyRepositorySettings

# REPOSITORY
from datetime import timedelta

import aiosqlite

from aiorequestful.cache.backend.sqlite import SQLiteTable

connection = aiosqlite.connect(database="file::memory:?cache=shared", uri=True)
settings = SpotifyRepositorySettings(name="tracks")

repository = SQLiteTable(
    connection=connection, settings=settings, expire=timedelta(weeks=2)
)

# END
# CACHE - INIT

import tempfile

from aiorequestful.cache.backend.sqlite import SQLiteCache

cache = SQLiteCache(
    cache_name="__IN_MEMORY__",
    connector=lambda: aiosqlite.connect(database="file::memory:?cache=shared", uri=True),
)

# END
# CACHE - CLASS METHOD INIT

cache = SQLiteCache.connect(value="file::memory:?cache=shared")
cache = SQLiteCache.connect_with_path(path=f"{tempfile.gettempdir()}/path/to/db.sqlite")
cache = SQLiteCache.connect_with_temp_db()
cache = SQLiteCache.connect_with_in_memory_db()

# END
