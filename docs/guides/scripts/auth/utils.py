# AUTH REQUEST - BASIC
from aiohttp import ClientSession

from aiorequestful.auth.utils import AuthRequest

auth_request = AuthRequest(method="GET", url="http://cool_service.com/authorise")


async def request(request: AuthRequest) -> None:
    async with ClientSession() as session:
        await request(session)
        await request.request(session)  # does the same as above


# END
# AUTH REQUEST - TEMP PARAMS

async def request_with_temporary_headers(request: AuthRequest, headers: dict[str, str]) -> None:
    with request.enrich_headers(headers):
        async with ClientSession() as session:
            await request(session)


# END
# AUTH RESPONSE - BASIC

import tempfile

from aiorequestful.auth.utils import AuthResponse

auth_response = AuthResponse(file_path=f"{tempfile.gettempdir()}/path/to/token/response")

auth_response.load_response_from_file()  # get the response from the file path
auth_response.replace({"access_token": "you_are_authorised", "token_type": "Bearer"})  # force add a new response
auth_response.save_response_to_file()  # save the response to file

auth_response.token  # extract the token
auth_response.headers  # generate the headers
auth_response["token_type"]  # access keys on the response directly

# END
# AUTH RESPONSE - ADVANCED

auth_response.pop("token_type")

# add additional headers to add to the generated headers to ensure successful requests
auth_response.additional_headers = {"Content-Type": "application/json"}
# set an optional fallback default for the token type if it cannot be found in the response
auth_response.token_prefix_default = "Basic"

assert auth_response.headers == {"Authorization": "Basic you_are_authorised", "Content-Type": "application/json"}

# END
# AUTH RESPONSE - ENRICH

auth_response["expires_in"] = 3600
auth_response.enrich()

auth_response["granted_at"]  # the time at which the token was granted at
auth_response["expires_at"]  # the time at which the token expires

# END
# AUTH TESTER - BASIC

from aiohttp import ClientResponse

from aiorequestful.auth.utils import AuthTester


async def response_test(response: ClientResponse) -> bool:
    return "error" not in response.text()

auth_tester = AuthTester(request=auth_request, response_test=response_test, max_expiry=120)


async def test(tester: AuthTester) -> bool:
    result = await tester.test(response=auth_response)
    result = await tester(response=auth_response)  # does the same as above
    return result

# END
# SOCKET HANDLER - BASIC

from aiorequestful.auth.utils import SocketHandler

socket_handler = SocketHandler(port=32000, timeout=60)

with socket_handler as socket_listener:
    data = socket_listener.recv(0)

# END
