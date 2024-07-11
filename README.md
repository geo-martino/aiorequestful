# aiorequestful

[![PyPI Version](https://img.shields.io/pypi/v/aiorequestful?logo=pypi&label=Latest%20Version)](https://pypi.org/project/aiorequestful)
[![Python Version](https://img.shields.io/pypi/pyversions/aiorequestful.svg?logo=python&label=Supported%20Python%20Versions)](https://pypi.org/project/aiorequestful/)
[![Documentation](https://img.shields.io/badge/Documentation-red.svg)](https://geo-martino.github.io/aiorequestful/)
</br>
[![PyPI Downloads](https://img.shields.io/pypi/dm/aiorequestful?label=Downloads)](https://pypi.org/project/aiorequestful/)
[![Code Size](https://img.shields.io/github/languages/code-size/geo-martino/aiorequestful?label=Code%20Size)](https://github.com/geo-martino/aiorequestful)
[![Contributors](https://img.shields.io/github/contributors/geo-martino/aiorequestful?logo=github&label=Contributors)](https://github.com/geo-martino/aiorequestful/graphs/contributors)
[![License](https://img.shields.io/github/license/geo-martino/aiorequestful?label=License)](https://github.com/geo-martino/aiorequestful/blob/master/LICENSE)
</br>
[![GitHub - Validate](https://github.com/geo-martino/aiorequestful/actions/workflows/validate.yml/badge.svg?branch=master)](https://github.com/geo-martino/aiorequestful/actions/workflows/validate.yml)
[![GitHub - Deployment](https://github.com/geo-martino/aiorequestful/actions/workflows/deploy.yml/badge.svg?event=release)](https://github.com/geo-martino/aiorequestful/actions/workflows/deploy.yml)
[![GitHub - Documentation](https://github.com/geo-martino/aiorequestful/actions/workflows/docs_publish.yml/badge.svg)](https://github.com/geo-martino/aiorequestful/actions/workflows/docs_publish.yml)

### An asynchronous HTTP and RESTful API requests framework for asyncio and Python

## Contents
* [Getting Started](#getting-started)
* [Currently Supported](#currently-supported)
* [Motivation and Aims](#motivation-and-aims)
* [Release History](#release-history)
* [Contributing and Reporting Issues](#contributing-and-reporting-issues)

> [!NOTE]  
> This readme provides a brief overview of the program. 
> [Read the docs](https://geo-martino.github.io/aiorequestful/) for full reference documentation.


## Installation
Install through pip using one of the following commands:

```bash
pip install aiorequestful
```
```bash
python -m pip install aiorequestful
```

There are optional dependencies that you may install for optional functionality. 
For the current list of optional dependency groups, [read the docs](https://geo-martino.github.io/aiorequestful/howto.install.html)


## Getting Started

These quick guides will help you get set up and going with aiorequestful in just a few minutes.
For more detailed guides, check out the [documentation](https://geo-martino.github.io/aiorequestful/).

***Coming soon...***


## Currently Supported

- **Cache Backends**: `SQLiteCache`
- **Basic Authorisation**: `BasicAuthoriser`
- **OAuth2 Flows**: `AuthorisationCodeFlow` `AuthorisationCodePKCEFlow` `ClientCredentialsFlow`


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
check out the [documentation](https://geo-martino.github.io/aiorequestful/release-history.html).


## Contributing and Reporting Issues

If you have any suggestions, wish to contribute, or have any issues to report, please do let me know 
via the issues tab or make a new pull request with your new feature for review. 

For more info on how to contribute to aiorequestful, 
check out the [documentation](https://geo-martino.github.io/aiorequestful/contributing.html).


I hope you enjoy using aiorequestful!
