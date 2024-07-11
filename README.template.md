# {program_name}

[![PyPI Version](https://img.shields.io/pypi/v/{program_name_lower}?logo=pypi&label=Latest%20Version)](https://pypi.org/project/{program_name_lower})
[![Python Version](https://img.shields.io/pypi/pyversions/{program_name_lower}.svg?logo=python&label=Supported%20Python%20Versions)](https://pypi.org/project/{program_name_lower}/)
[![Documentation](https://img.shields.io/badge/Documentation-red.svg)](https://{program_owner_user}.github.io/{program_name_lower}/)
</br>
[![PyPI Downloads](https://img.shields.io/pypi/dm/{program_name_lower}?label=Downloads)](https://pypi.org/project/{program_name_lower}/)
[![Code Size](https://img.shields.io/github/languages/code-size/{program_owner_user}/{program_name_lower}?label=Code%20Size)](https://github.com/geo-martino/{program_name_lower})
[![Contributors](https://img.shields.io/github/contributors/{program_owner_user}/{program_name_lower}?logo=github&label=Contributors)](https://github.com/{program_owner_user}/{program_name_lower}/graphs/contributors)
[![License](https://img.shields.io/github/license/{program_owner_user}/{program_name_lower}?label=License)](https://github.com/geo-martino/{program_name_lower}/blob/master/LICENSE)
</br>
[![GitHub - Validate](https://github.com/geo-martino/{program_name_lower}/actions/workflows/validate.yml/badge.svg?branch=master)](https://github.com/{program_owner_user}/{program_name_lower}/actions/workflows/validate.yml)
[![GitHub - Deployment](https://github.com/{program_owner_user}/{program_name_lower}/actions/workflows/deploy.yml/badge.svg?event=release)](https://github.com/{program_owner_user}/{program_name_lower}/actions/workflows/deploy.yml)
[![GitHub - Documentation](https://github.com/{program_owner_user}/{program_name_lower}/actions/workflows/docs_publish.yml/badge.svg)](https://github.com/{program_owner_user}/{program_name_lower}/actions/workflows/docs_publish.yml)

### An asynchronous HTTP and RESTful API requests framework for asyncio and Python

## Contents
* [Getting Started](#getting-started)
* [Currently Supported](#currently-supported)
* [Motivation and Aims](#motivation-and-aims)
* [Release History](#release-history)
* [Contributing and Reporting Issues](#contributing-and-reporting-issues)

> [!NOTE]  
> This readme provides a brief overview of the program. 
> [Read the docs](https://{program_owner_user}.github.io/{program_name_lower}/) for full reference documentation.


## Installation
Install through pip using one of the following commands:

```bash
pip install {program_name_lower}
```
```bash
python -m pip install {program_name_lower}
```

There are optional dependencies that you may install for optional functionality. 
For the current list of optional dependency groups, [read the docs](https://{program_owner_user}.github.io/{program_name_lower}/howto.install.html)


## Getting Started

These quick guides will help you get set up and going with {program_name} in just a few minutes.
For more detailed guides, check out the [documentation](https://{program_owner_user}.github.io/{program_name_lower}/).

### Sending requests

Ultimately, the core part of this whole package is the `RequestHandler`.
This object will handle, amongst other things, these core processes:

* creating sessions
* sending requests
* processing responses as configured
* handling error responses including backoff/retry/wait time
* authorising if configured
* caching responses if configured

Each part listed above can be configured as required.
Before we get to that though, let's start with a simple example.


### Sending a simple request

```python
import asyncio
from typing import Any

from yarl import URL

from aiorequestful.request.handler import RequestHandler


async def send_get_request(handler: RequestHandler, url: str | URL) -> Any:
    """Sends a simple GET request using the given ``handler`` for the given ``url``."""
    async with handler:
        payload = await handler.get(url)

    return payload


request_handler: RequestHandler = RequestHandler.create()
api_url = "https://official-joke-api.appspot.com/jokes/programming/random"
task = send_get_request(request_handler, url=api_url)
result = asyncio.run(task)

print(result)
print(type(result).__name__)
```

Here, we request some data from an open API that requires no authentication to access.
Notice how the data type of the object we retrieve is a string, but we can see from the print
that this is meant to be JSON data.


### Handling the response payload

When we know the data type we want to retrieve, we can assign a `PayloadHandler`
to the `RequestHandler` to retrieve the data type we require.

```python
from aiorequestful.response.payload import JSONPayloadHandler

payload_handler = JSONPayloadHandler()
request_handler.payload_handler = payload_handler

task = send_get_request(request_handler, url=api_url)
result = asyncio.run(task)

print(result)
print(type(result).__name__)
```

By doing so, we ensure that our `RequestHandler` only returns data in a format that we expect.
The `JSONPayloadHandler` is set to fail if the data given to it is not valid JSON data.

> [!NOTE]
> For more info on payload handling, [read the docs](https://{program_owner_user}.github.io/{program_name_lower}/guides/response.html#payload).


### Authorising with the service

Usually, most REST APIs require a user to authenticate and authorise with their services before making any requests.
We can assign an `Authoriser` to the `RequestHandler` to handle authorising for us.

```python
from aiorequestful.auth.basic import BasicAuthoriser


async def auth_and_send_get_request(handler: RequestHandler, url: str) -> Any:
    """Authorise the ``handler`` with the service before sending a GET request to the given ``url``."""
    async with handler:
        await handler.authorise()
        payload = await handler.get(url)

    return payload


authoriser = BasicAuthoriser(login="username", password="password")
request_handler.authoriser = authoriser

task = auth_and_send_get_request(request_handler, url=api_url)
result = asyncio.run(task)

print(result)
```

> [!NOTE]
> For more info on authorising including other types of supported authorisation flows, [read the docs](https://{program_owner_user}.github.io/{program_name_lower}/guides/auth.html#auth).


### Caching responses

When requesting a large amount of requests from a REST API, you will often find it is comparatively slow for it
to respond.

You may add a `ResponseCache` to the `RequestHandler` to cache the initial responses from
these requests.
This will help speed up future requests by hitting the cache for requests first and returning any matching response
from the cache first before making a HTTP request to get the data.

```python
from aiorequestful.cache.backend import SQLiteCache

cache = SQLiteCache.connect_with_in_memory_db()
request_handler = RequestHandler.create(cache=cache)

task = send_get_request(request_handler, url=api_url)
result = asyncio.run(task)

print(result)
```

However, this example will not cache anything as we have not set up repositories for the endpoints we require.
See :ref:`guide-cache` for more info on settings up cache repositories.

> [!NOTE]
> We cannot dynamically assign a cache to a instance of `RequestHandler`.
> Hence, we always need to supply the `ResponseCache` when instantiating the `RequestHandler`.

> [!NOTE]
> For more info on setting a successful cache and other supported cache backends, [read the docs](https://{program_owner_user}.github.io/{program_name_lower}/guides/cache.html#cache).


### Handling error responses

Often, we will receive error responses that we will need to handle.
We can have the :py:class:`RequestHandler` handle these responses by assigning `StatusHandler` objects.

```python
from aiorequestful.response.status import ClientErrorStatusHandler, UnauthorisedStatusHandler, RateLimitStatusHandler

response_handlers = [
    UnauthorisedStatusHandler(), RateLimitStatusHandler(), ClientErrorStatusHandler()
]
request_handler.response_handlers = response_handlers

task = send_get_request(request_handler, url=api_url)
result = asyncio.run(task)

print(result)
print(type(result).__name__)
```

> [!NOTE]
> For more info on `StatusHandler` and how they handle each response type, [read the docs](https://{program_owner_user}.github.io/{program_name_lower}/guides/response.html#status).


### Managing retries and backoff time

Another way we can ensure a successful response is to include a retry and backoff time management strategy.

The `RequestHandler` provides two key mechanisms for these operations:

* The `wait_timer` manages the time to wait after every request whether successful or not.
  This is **object-bound** i.e. any increase to this timer affects future requests.
* The `retry_timer` manages the time to wait after each unsuccessful and unhandled request.
  This is **request-bound** i.e. any increase to this timer only affects the current request and not future requests.

#### Retries and unsuccessful backoff time

As an example, if we want to simply retry the same request 3 times without any backoff time in-between each request,
we can set the following.

```python
from aiorequestful.request.timer import StepCountTimer

request_handler.retry_timer = StepCountTimer(initial=0, count=3, step=0)
```

We set the ``count`` value to ``3`` for 3 retries and all other values to ``0`` to ensure there is no wait time between
these retries.

Should we wish to add some time between each retry, we can do the following.

```python
request_handler.retry_timer = StepCountTimer(initial=0, count=3, step=0.2)
```

This will now add 0.2 seconds between each unsuccessful request, waiting 0.6 seconds before the final retry for example.

This timer is generated as new for each new request so any increase in time
**does not carry through to future requests**.

#### Wait backoff time

We may also wish to handle wait time after all requests.
This can be useful for sensitive services that often return 'Too Many Requests' errors when making a large volume
of requests at once.

```python
from aiorequestful.request.timer import StepCeilingTimer

request_handler.wait_timer = StepCeilingTimer(initial=0, final=1, step=0.1)
```

This timer will increase by 0.1 seconds each time it is increased up to a maximum of 1 second.

> [!WARNING]
> The `RequestHandler` is not responsible for handling when this timer is increased.
> A `StatusHandler` should be used to increase this timer such as the `RateLimitStatusHandler`
> which will increase this timer every time a 'Too Many Requests' error is returned.

This timer is the same for each new request so any increase in time
**does carry through to future requests**.

> [!NOTE]
> For more info on the available `Timer` objects, [read the docs](https://{program_owner_user}.github.io/{program_name_lower}/guides/timer.html#timer).


## Currently Supported

- **Cache Backends**: {cache_backends}
- **Basic Authorisation**: {basic_auth}
- **OAuth2 Flows**: {oauth2}


## Motivation and Aims

The key aim of this package is to provide a common, performant framework for interacting with REST API services 
and other HTTP frameworks.

As a new developer, I found it incredibly confusing understanding the myriad ways one can authenticate with a REST API, 
which to select for my use case, how to implement it in code and so on. 
I then found it a great challenge learning how to get the maximum performance from my applications for HTTP requests 
while balancing this against issues when accessing sensitive services which often return 'Too Many Requests' 
type errors as I improved the performance of my applications.
As such, I separated out all the code relating to HTTP requests into this package so that other developers can use 
what I have learned in their applications too.

This package should implement the following:
- all possible authorisation flows for these types of services
- intelligent caching per endpoint for these responses to many common and appropriate cache backends to allow for:
  - storing of responses in a 
  - reduction in request-response times by retrieving responses from the cache instead of HTTP requests
  - reducing load on sensitive HTTP-based services by hitting the cache instead, 
    thereby reducing 'Too Many Requests' type errors
- automatic handling of common HTTP error status codes to ensure guaranteed successful requests
- other quality of life additions to ensure a large volume of responses are returned in the fastest possible time 
  e.g. backoff/retry/wait timers

In so doing, I hope to make the access of data from these services as seamless as possible and provide the foundation 
of this part of the process in future applications and use cases.


## Release History

For change and release history, 
check out the [documentation](https://{program_owner_user}.github.io/{program_name_lower}/release-history.html).


## Contributing and Reporting Issues

If you have any suggestions, wish to contribute, or have any issues to report, please do let me know 
via the issues tab or make a new pull request with your new feature for review. 

For more info on how to contribute to {program_name}, 
check out the [documentation](https://{program_owner_user}.github.io/{program_name_lower}/contributing.html).


I hope you enjoy using {program_name}!
