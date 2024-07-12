# BASIC

from aiorequestful.cache.backend.sqlite import SQLiteCache
from aiorequestful.cache.session import CachedSession


cache = SQLiteCache.connect_with_in_memory_db()
session = CachedSession(cache=cache)

# END
