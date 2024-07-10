"""
Implements basic authoriser flows.
"""
import base64

from aiorequestful.auth.base import Authoriser, _DEFAULT_SERVICE_NAME
from aiorequestful.types import Headers


class BasicAuthoriser(Authoriser):
    """
    Authorise HTTP requests using basic authentication i.e. username + password (optional)

    :param service_name: The service name for which to authorise.
    :param login: The login ID of the credentials.
    :param password: The login password.
    :param encoding: The encoding to apply to credentials when sending requests.
    """

    __slots__ = ("login", "password", "encoding")

    def __init__(
            self,
            login: str,
            password: str = "",
            encoding: str = "latin1",
            service_name: str = _DEFAULT_SERVICE_NAME
    ):
        super().__init__(service_name=service_name)

        #: The login ID of the credentials.
        self.login = login
        #: The login password.
        self.password = password
        #: The encoding to apply to credentials when sending requests.
        self.encoding = encoding

    async def authorise(self) -> Headers:
        credentials = f"{self.login}:{self.password}".encode(self.encoding)
        credentials_encoded = base64.b64encode(credentials).decode(self.encoding)
        return {
            "Authorization": f"Basic {credentials_encoded}"
        }


BASIC_CLASSES: frozenset[type[Authoriser]] = frozenset({
    BasicAuthoriser,
})
