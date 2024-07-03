"""
Exceptions relating to API operations.
"""
from typing import Any

from aiohttp import ClientResponse


class AIORequestsError(Exception):
    """Generic base class for all aiorequestful-related errors"""


class InputError(AIORequestsError, ValueError):
    """Exception raised when the given input is invalid."""


class MethodError(InputError):
    """Exception raised for unrecognised method values."""
    def __init__(self, value: Any = None, message: str = "Unrecognised method"):
        self.value = value
        if value is not None:
            message = f"{message}: {value}"
        super().__init__(message)


class AIORequestsImportError(AIORequestsError, ImportError):
    """Exception raised for import errors, usually from missing modules."""


###########################################################################
## HTTP Requests errors
###########################################################################
class HTTPError(AIORequestsError):
    """Exception raised for generic HTTP errors."""


class RequestError(HTTPError):
    """Exception raised for errors relating to HTTP requests."""


class ResponseError(HTTPError):
    """
    Exception raised for errors relating to responses from HTTP requests.

    :param message: Explanation of the error.
    :param response: The :py:class:`ClientResponse` related to the error.
    """
    def __init__(self, message: str | None = None, response: ClientResponse | None = None):
        self.message = message
        self.response = response
        formatted = f"Status code: {response.status} | {message}" if response else message
        super().__init__(formatted)


###########################################################################
## Authoriser errors
###########################################################################
class AuthoriserError(AIORequestsError):
    """Exception raised for errors relating to authorisation."""


###########################################################################
## Cache errors
###########################################################################
class CacheError(AIORequestsError):
    """Exception raised for errors relating to the cache."""
