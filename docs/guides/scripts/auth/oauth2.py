# BASE

import tempfile

from aiorequestful.auth.oauth2 import OAuth2Authoriser
from aiorequestful.auth.utils import AuthRequest, AuthResponse, AuthTester

token_request = AuthRequest(method="POST", url="https://cool_service.com/api/token")
response_handler = AuthResponse(file_path=f"{tempfile.gettempdir()}/path/to/token/response")
response_tester = AuthTester(max_expiry=1800)

authoriser = OAuth2Authoriser(
    token_request=token_request, response_handler=response_handler, response_tester=response_tester
)

# END
# CLIENT CREDENTIALS - INIT

from aiorequestful.auth.oauth2 import ClientCredentialsFlow

authoriser = ClientCredentialsFlow(
    token_request=token_request, response_handler=response_handler, response_tester=response_tester
)

# END
# CLIENT CREDENTIALS - CREATE

authoriser = ClientCredentialsFlow.create(
    service_name="Cool Service",
    token_request_url="https://cool_service.com/api/token",
    client_id="<YOUR CLIENT ID>",
    client_secret="<YOUR CLIENT SECRET>",
)

# assign additional attributes as necessary
authoriser.response = response_handler
authoriser.tester = response_tester

# END
# CLIENT CREDENTIALS - CREATE ENCODED

authoriser = ClientCredentialsFlow.create_with_encoded_credentials(
    service_name="Cool Service",
    token_request_url="https://cool_service.com/api/token",
    client_id="<YOUR CLIENT ID>",
    client_secret="<YOUR CLIENT SECRET>",
)

# assign additional attributes as necessary
authoriser.response = response_handler
authoriser.tester = response_tester

# END
# AUTHORISATION CODE - INIT

from aiorequestful.auth.oauth2 import AuthorisationCodeFlow
from aiorequestful.auth.utils import SocketHandler

user_request = AuthRequest(method="POST", url="https://cool_service.com/authorise")
refresh_request = AuthRequest(method="POST", url="https://cool_service.com/api/token/refresh")
socket_handler = SocketHandler(port=32000, timeout=60)  # the local socket to receive the authorisation code redirect
redirect_uri = "https://myapp.com/authorise"  # the public address of your app

authoriser = AuthorisationCodeFlow(
    user_request=user_request,
    redirect_uri=redirect_uri,
    token_request=token_request,
    refresh_request=refresh_request,
    response_handler=response_handler,
    response_tester=response_tester,
    socket_handler=socket_handler,
)


# END
# AUTHORISATION CODE - CREATE

authoriser = AuthorisationCodeFlow.create(
    service_name="Cool Service",
    user_request_url="https://cool_service.com/authorise",
    token_request_url="https://cool_service.com/api/token",
    refresh_request_url="https://cool_service.com/api/token/refresh",
    client_id="<YOUR CLIENT ID>",
    client_secret="<YOUR CLIENT SECRET>",
    scope=["public-user-data", "private-user-data"]
)

# assign additional attributes as necessary
authoriser.response = response_handler
authoriser.tester = response_tester
authoriser.redirect_uri = redirect_uri
authoriser.socket_handler = socket_handler


# END
# AUTHORISATION CODE - CREATE ENCODED

authoriser = AuthorisationCodeFlow.create_with_encoded_credentials(
    service_name="Cool Service",
    user_request_url="https://cool_service.com/authorise",
    token_request_url="https://cool_service.com/api/token",
    refresh_request_url="https://cool_service.com/api/token/refresh",
    client_id="<YOUR CLIENT ID>",
    client_secret="<YOUR CLIENT SECRET>",
    scope=["public-user-data", "private-user-data"]
)

# assign additional attributes as necessary
authoriser.response = response_handler
authoriser.tester = response_tester
authoriser.redirect_uri = redirect_uri
authoriser.socket_handler = socket_handler


# END
# AUTHORISATION CODE WITH PKCE - INIT

from aiorequestful.auth.oauth2 import AuthorisationCodePKCEFlow

user_request = AuthRequest(method="POST", url="https://cool_service.com/authorise")
refresh_request = AuthRequest(method="POST", url="https://cool_service.com/api/token/refresh")
socket_handler = SocketHandler(port=32000, timeout=60)  # the local socket to receive the authorisation code redirect
redirect_uri = "https://myapp.com/authorise"  # the public address of your app

authoriser = AuthorisationCodePKCEFlow(
    user_request=user_request,
    redirect_uri=redirect_uri,
    token_request=token_request,
    refresh_request=refresh_request,
    response_handler=response_handler,
    response_tester=response_tester,
    socket_handler=socket_handler,
    pkce_code_length=128,
)

# END
# AUTHORISATION CODE WITH PKCE - CREATE

authoriser = AuthorisationCodePKCEFlow.create(
    service_name="Cool Service",
    user_request_url="https://cool_service.com/authorise",
    redirect_uri="https://myapp.com/authorise",
    token_request_url="https://cool_service.com/api/token",
    refresh_request_url="https://cool_service.com/api/token/refresh",
    client_id="<YOUR CLIENT ID>",
    client_secret="<YOUR CLIENT SECRET>",
    scope=["public-user-data", "private-user-data"],
)

# assign additional attributes as necessary
authoriser.response = response_handler
authoriser.tester = response_tester
authoriser.redirect_uri = redirect_uri
authoriser.socket_handler = socket_handler


# END
# AUTHORISATION CODE WITH PKCE - CREATE ENCODED

authoriser = AuthorisationCodePKCEFlow.create_with_encoded_credentials(
    service_name="Cool Service",
    user_request_url="https://cool_service.com/authorise",
    token_request_url="https://cool_service.com/api/token",
    refresh_request_url="https://cool_service.com/api/token/refresh",
    client_id="<YOUR CLIENT ID>",
    client_secret="<YOUR CLIENT SECRET>",
    scope=["public-user-data", "private-user-data"]
)

# assign additional attributes as necessary
authoriser.response = response_handler
authoriser.tester = response_tester
authoriser.redirect_uri = redirect_uri
authoriser.socket_handler = socket_handler


# END
