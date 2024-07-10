"""
Exceptions relating to authoriser operations.
"""
from aiorequestful.exception import AIORequestfulError


class AuthoriserError(AIORequestfulError):
    """Exception raised for errors relating to authorisation."""
