# BASIC

from aiorequestful.cache.backend.base import ResponseRepositorySettings

settings = ResponseRepositorySettings(name="main")

# END
# PAYLOAD

from aiorequestful.response.payload import JSONPayloadHandler

payload_handler = JSONPayloadHandler()
settings = ResponseRepositorySettings(name="main", payload_handler=payload_handler)

# END
