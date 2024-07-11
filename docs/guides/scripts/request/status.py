from simple import *

# PART 1

from aiorequestful.response.status import ClientErrorStatusHandler, UnauthorisedStatusHandler, RateLimitStatusHandler

response_handlers = [
    UnauthorisedStatusHandler(), RateLimitStatusHandler(), ClientErrorStatusHandler()
]
request_handler.response_handlers = response_handlers

task = send_get_request(request_handler, url=api_url)
result = asyncio.run(task)

print(result)
print(type(result).__name__)

# PART 2

request_handler = RequestHandler.create(response_handlers=response_handlers)

task = send_get_request(request_handler, url=api_url)
result = asyncio.run(task)

print(result)
print(type(result).__name__)

# PART 3

response_handlers = [
    ClientErrorStatusHandler(), UnauthorisedStatusHandler(), RateLimitStatusHandler()
]
request_handler.response_handlers = response_handlers

task = send_get_request(request_handler, url=api_url)
result = asyncio.run(task)

print(result)
print(type(result).__name__)
