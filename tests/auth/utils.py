from aiorequestful.auth import Authoriser
from aiorequestful.types import Headers

response_enrich_keys = ("granted_at", "expires_at", "refresh_token")


class MockAuthoriser(Authoriser):
    async def authorise(self) -> Headers:
        return {"Authorization": "Basic test"}
