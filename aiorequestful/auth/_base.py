import logging
from abc import ABC, abstractmethod
from collections.abc import Awaitable

from aiorequestful.types import Headers


class Authoriser(ABC):
    """
    Base interface for authenticating and authorising access to a service over HTTP.

    :param service_name: The service name for which to authorise.
    """

    def __init__(self, service_name: str = "unknown service"):
        #: The :py:class:`logging.Logger` for this  object
        self.logger: logging.Logger = logging.getLogger(__name__)

        #: The service name for which to authorise. Currently only used for logging purposes.
        self.service_name = service_name

    @abstractmethod
    async def authorise(self) -> Headers:
        """
        Authenticate and authorise, testing/refreshing/re-authorising as needed.

        :raise APIError: If the token cannot be generated or validated.
        """
        raise NotImplementedError

    def __call__(self) -> Awaitable[Headers]:
        return self.authorise()
