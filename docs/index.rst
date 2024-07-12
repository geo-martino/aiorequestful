=========================
Welcome to aiorequestful!
=========================

An Asynchronous HTTP and RESTful API requests framework for asyncio and Python
------------------------------------------------------------------------------

* Full implementation of authorisation handling for authorising with any HTTP service, including OAuth2 flows
* Automatic response payload caching and cache retrieval on a per-endpoint basis to allow fine control over
  how and when response data is cached
* Customisable payload response handling to transform responses before returning and caching
* Automatic handling of common HTTP error status codes to ensure guaranteed successful requests
* Formulaic approach to retries and backoff handling to ensure smooth requests on sensitive services to handle
  'Too Many Requests' style errors


What's in this documentation
----------------------------

* Guides on getting started with aiorequestful and other key functionality of the package (*Coming soon...*)
* Release history
* How to get started with contributing to aiorequestful
* Reference documentation

.. include:: guides/install.rst
   :start-after: :

.. toctree::
   :maxdepth: 1
   :caption: 📜 Guides & Getting Started

   guides/install
   guides/request
   guides/response
   guides/auth
   guides/cache
   guides/timer

.. toctree::
   :maxdepth: 1
   :caption: 🛠️ Project Info

   info/release-history
   info/contributing

.. toctree::
   :maxdepth: 1
   :caption: 📖 Reference

   reference/aiorequestful.auth
   reference/aiorequestful.cache
   reference/aiorequestful.request
   reference/aiorequestful.response
   reference/aiorequestful.exception
   reference/aiorequestful.types

   genindex
