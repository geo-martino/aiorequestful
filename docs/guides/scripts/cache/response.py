# BASIC

import json

from aiohttp import ClientRequest
from yarl import URL

from aiorequestful.cache.response import CachedResponse

url = URL("https://official-joke-api.appspot.com/jokes/programming/random")
request = ClientRequest(method="GET", url=url)
payload = [
    {
        "type": "programming",
        "setup": "I was gonna tell you a joke about UDP...",
        "punchline": "...but you might not get it.",
        "id": 72
    }
]

response = CachedResponse(request, payload=json.dumps(payload))

# END
