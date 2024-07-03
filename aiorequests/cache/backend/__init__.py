from aiorequests.cache.backend.base import ResponseCache
from aiorequests.cache.backend.sqlite import SQLiteCache

CACHE_CLASSES: frozenset[type[ResponseCache]] = frozenset({SQLiteCache})
CACHE_TYPES = frozenset(cls.type for cls in CACHE_CLASSES)
