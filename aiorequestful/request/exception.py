"""
Exceptions relating to request operations.
"""
from aiorequestful.exception import HTTPError


class RequestError(HTTPError):
    """Exception raised for errors relating to HTTP requests."""
