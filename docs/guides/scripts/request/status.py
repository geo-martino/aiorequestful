from docs.guides.scripts.request._base import *

# ASSIGNMENT

from aiorequestful.response.status import ClientErrorStatusHandler, UnauthorisedStatusHandler, RateLimitStatusHandler

response_handlers = [
    UnauthorisedStatusHandler(), RateLimitStatusHandler(), ClientErrorStatusHandler()
]
request_handler.response_handlers = response_handlers

task = send_get_request(request_handler, url=api_url)
result = asyncio.run(task)

print(result)
print(type(result).__name__)

# END
# INSTANTIATION

request_handler = RequestHandler.create(response_handlers=response_handlers)

task = send_get_request(request_handler, url=api_url)
result = asyncio.run(task)

print(result)
print(type(result).__name__)

# END
# REORDER

response_handlers = [
    ClientErrorStatusHandler(), UnauthorisedStatusHandler(), RateLimitStatusHandler()
]
request_handler.response_handlers = response_handlers

task = send_get_request(request_handler, url=api_url)
result = asyncio.run(task)

print(result)
print(type(result).__name__)

# END
