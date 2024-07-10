"""
Exceptions relating to cache operations.
"""
from aiorequestful.exception import AIORequestfulError


class CacheError(AIORequestfulError):
    """Exception raised for errors relating to the cache."""
