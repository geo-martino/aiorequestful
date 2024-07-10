"""
Exceptions relating to response operations.
"""
from aiohttp import ClientResponse

from aiorequestful.exception import AIORequestfulError, HTTPError


class ResponseError(HTTPError):
    """
    Exception raised for errors relating to responses from HTTP requests.

    :param message: Explanation of the error.
    :param response: The :py:class:`ClientResponse` related to the error.
    """
    def __init__(self, message: str = None, response: ClientResponse | None = None):
        self.message = message
        self.response = response
        formatted = f"Status code: {response.status} | {message}" if response else message
        super().__init__(formatted)


class PayloadHandlerError(AIORequestfulError):
    """Error raised when handling a response's payload."""


class StatusHandlerError(AIORequestfulError):
    """Error raised when handling a response based on its status code."""
