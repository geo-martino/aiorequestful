from docs.guides.scripts.request._base import *

# ASSIGNMENT

from aiorequestful.response.payload import JSONPayloadHandler

payload_handler = JSONPayloadHandler()
request_handler.payload_handler = payload_handler

task = send_get_request(request_handler, url=api_url)
result = asyncio.run(task)

print(result)
print(type(result).__name__)

# END
# INSTANTIATION

request_handler = RequestHandler.create(payload_handler=payload_handler)

task = send_get_request(request_handler, url=api_url)
result = asyncio.run(task)

print(result)
print(type(result).__name__)

# END
