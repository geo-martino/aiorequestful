from docs.guides.scripts.request._base import *

# ASSIGNMENT - RETRY NO TIME

from aiorequestful.timer import StepCountTimer

request_handler.retry_timer = StepCountTimer(initial=0, count=3, step=0)

# END
# ASSIGNMENT - RETRY WITH TIME

request_handler.retry_timer = StepCountTimer(initial=0, count=3, step=0.2)

# END
# ASSIGNMENT - WAIT

from aiorequestful.timer import StepCeilingTimer

request_handler.wait_timer = StepCeilingTimer(initial=0, final=1, step=0.1)

# END
# INSTANTIATION

retry_timer = StepCountTimer(initial=0, count=3, step=0.2)
wait_timer = StepCeilingTimer(initial=0, final=1, step=0.1)
request_handler = RequestHandler.create(retry_timer=retry_timer, wait_timer=wait_timer)

task = send_get_request(request_handler, url=api_url)
result = asyncio.run(task)

print(result)

# END
