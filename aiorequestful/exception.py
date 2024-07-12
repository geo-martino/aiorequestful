"""
Core exceptions for the entire package.
"""


class AIORequestfulError(Exception):
    """Generic base class for all aiorequestful-related errors"""


class InputError(AIORequestfulError, ValueError):
    """Exception raised when the given input is invalid."""


class AIORequestfulImportError(AIORequestfulError, ImportError):
    """Exception raised for import errors, usually from missing modules."""


class HTTPError(AIORequestfulError):
    """Exception raised for generic HTTP errors."""


class RequestError(HTTPError):
    """Exception raised for errors relating to HTTP requests."""
