from simple import *

# PART 1

from aiorequestful.timer import StepCountTimer

request_handler.retry_timer = StepCountTimer(initial=0, count=3, step=0)

# PART 2

request_handler.retry_timer = StepCountTimer(initial=0, count=3, step=0.2)

# PART 3

from aiorequestful.timer import StepCeilingTimer

request_handler.wait_timer = StepCeilingTimer(initial=0, final=1, step=0.1)

# PART 4

retry_timer = StepCountTimer(initial=0, count=3, step=0.2)
wait_timer = StepCeilingTimer(initial=0, final=1, step=0.1)
request_handler = RequestHandler.create(retry_timer=retry_timer, wait_timer=wait_timer)

task = send_get_request(request_handler, url=api_url)
result = asyncio.run(task)

print(result)
