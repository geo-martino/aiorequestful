"""
Base interface for implementations of all authoriser flows.
"""
import logging
from abc import ABC, abstractmethod
from collections.abc import Awaitable
from typing import Generator, Any

from aiorequestful.types import Headers

_DEFAULT_SERVICE_NAME = "unknown_service"


class Authoriser(ABC):
    """
    Base interface for authenticating and authorising access to a service over HTTP.

    :param service_name: The service name for which to authorise.
    """

    __slots__ = ("logger", "service_name")

    def __init__(self, service_name: str = _DEFAULT_SERVICE_NAME):
        #: The :py:class:`logging.Logger` for this  object
        self.logger: logging.Logger = logging.getLogger(__name__)

        #: The service name for which to authorise. Currently only used for logging purposes.
        self.service_name = service_name

    @abstractmethod
    async def authorise(self) -> Headers:
        """
        Authenticate and authorise, testing/refreshing/re-authorising as needed.

        :raise AuthoriserError: If the authorisation failed to generate valid a token if needed,
            or if the tests continue to fail despite authorising/re-authorising.
        """
        raise NotImplementedError

    def __call__(self) -> Awaitable[Headers]:
        return self.authorise()

    def __await__(self) -> Generator[Any, None, Headers]:
        return self.authorise().__await__()
