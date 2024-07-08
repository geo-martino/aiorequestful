import base64

import pytest

from aiorequestful.auth.basic import BasicAuthoriser


class TestBasicAuthoriser:
    @pytest.fixture
    def authoriser(self) -> BasicAuthoriser:
        return BasicAuthoriser(
            login="test",
            password="password"
        )

    async def test_authorise(self, authoriser: BasicAuthoriser):
        headers = await authoriser.authorise()
        auth_type, credentials_encoded = headers["Authorization"].split()

        assert auth_type == "Basic"

        credentials = base64.b64decode(
            credentials_encoded.encode("ascii"), validate=True
        ).decode(authoriser.encoding)
        actual_login, actual_password = credentials.split(":")

        assert actual_login == authoriser.login
        assert actual_password == authoriser.password
