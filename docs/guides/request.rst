.. _request-guide:

Sending requests
================

Ultimately, the core part of this whole package is the :py:class:`.RequestHandler` found in the :py:mod:`.request` module.
This object will handle, amongst other things, these core processes:

* creating sessions
* sending requests
* processing responses as configured
* handling error responses including backoff/retry time
* authorising if configured
* caching responses if configured

Each part listed above can be configured as required.
Before we get to that though, let's start with a simple example.


Sending simple requests
-----------------------

.. literalinclude:: scripts/request/simple.py
   :language: Python
   :start-after: # SINGLE
   :end-before: # END

To send many requests, we simply do the following:

.. literalinclude:: scripts/request/simple.py
   :language: Python
   :start-after: # MANY
   :end-before: # END

.. note::
   Here we use the :py:meth:`.RequestHandler.create` class method to create the object.
   We can create the object directly, by providing a ``connector`` to a
   `ClientSession <https://docs.aiohttp.org/en/stable/client_reference.html#aiohttp.ClientSession>`_ as seen below,
   however it is preferable to use the :py:meth:`.RequestHandler.create` class method to automatically generate the ``connector``
   from the given kwargs.

   .. literalinclude:: scripts/request/simple.py
      :language: Python
      :start-after: # INIT
      :end-before: # END

Here, we requested some data from an open API that requires no authentication to access.
Notice how the data type of the object we retrieve is a string, but we can see from the print
that this is meant to be JSON data.


.. _request-payload:

Handling the response payload
-----------------------------

When we know the data type we want to retrieve, we can assign a :py:class:`.PayloadHandler`
to the :py:class:`.RequestHandler` to retrieve the data type we require.

.. literalinclude:: scripts/request/payload.py
   :language: Python
   :start-after: # ASSIGNMENT
   :end-before: # END

By doing so, we ensure that our :py:class:`.RequestHandler` only returns data in a format that we expect.
The :py:class:`.JSONPayloadHandler` is set to fail if the data given to it is not valid JSON data.

We may also assign this :py:class:`.PayloadHandler` when we create the :py:class:`.RequestHandler` too.

.. literalinclude:: scripts/request/payload.py
   :language: Python
   :start-after: # INSTANTIATION
   :end-before: # END

Additionally, if we have a :py:class:`.ResponseCache` set up on the :py:class:`.RequestHandler`,
the :py:class:`.PayloadHandler` for each :py:class:`.ResponseRepository` will also be updated as shown below.

.. literalinclude:: /../aiorequestful/request.py
   :language: Python
   :pyobject: RequestHandler.payload_handler
   :dedent: 4

.. seealso::
   For more info on setting up on how a :py:class:`.ResponseRepository` uses the :py:class:`.PayloadHandler`,
   see :ref:`cache-guide`.

.. seealso::
   For more info on payload handling, see :ref:`payload-guide`.


.. _request-auth:

Authorising with the service
----------------------------

Usually, most REST APIs require a user to authenticate and authorise with their services before making any requests.
We can assign an :py:class:`.Authoriser` to the :py:class:`.RequestHandler` to handle authorising for us.

.. literalinclude:: scripts/request/auth.py
   :language: Python
   :start-after: # ASSIGNMENT
   :end-before: # END

We may also assign this :py:class:`.Authoriser` when we create the :py:class:`.RequestHandler` too.

.. literalinclude:: scripts/request/auth.py
   :language: Python
   :start-after: # INSTANTIATION
   :end-before: # END

.. seealso::
   For more info on authorising including other types of supported authorisation flows, see :ref:`auth-guide`.


.. _request-cache:

Caching responses
-----------------

When requesting a large amount of requests from a REST API, you will often find it is comparatively slow for it
to respond.

You may add a :py:class:`.ResponseCache` to the :py:class:`.RequestHandler` to cache the initial responses from
these requests.
This will help speed up future requests by hitting the cache for requests first and returning any matching response
from the cache first before making an HTTP request to get the data.

.. literalinclude:: scripts/request/cache.py
   :language: Python
   :start-after: # INSTANTIATION
   :end-before: # END

However, this example will not cache anything as we have not set up repositories for the endpoints we require.
See :ref:`cache-guide` for more info on setting up cache repositories.

.. note::
   We cannot dynamically assign a cache to an instance of :py:class:`.RequestHandler`.
   Hence, we always need to supply the :py:class:`.ResponseCache` when instantiating the :py:class:`.RequestHandler`.

.. seealso::
   For more info on setting a successful cache and other supported cache backends, see :ref:`cache-guide`.


.. _request-status:

Handling error responses
------------------------

Often, we will receive error responses that we will need to handle.
We can have the :py:class:`.RequestHandler` handle these responses by assigning :py:class:`.StatusHandler` objects.

.. literalinclude:: scripts/request/status.py
   :language: Python
   :start-after: # ASSIGNMENT
   :end-before: # END

We may also assign these :py:class:`.StatusHandler` objects when we create the :py:class:`.RequestHandler` too.

.. literalinclude:: scripts/request/status.py
   :language: Python
   :start-after: # INSTANTIATION
   :end-before: # END

.. note::
   The order of the :py:class:`.StatusHandler` objects is important in determining which one has priority to
   handle a response when the status codes of the :py:class:`.StatusHandler` objects overlap.

   In this example, the :py:class:`.ClientErrorStatusHandler` is responsible for handling all client error status codes
   i.e. ``400``-``499``, the :py:class:`.UnauthorisedStatusHandler` is responsible for ``401`` status codes and the
   :py:class:`.RateLimitStatusHandler` is responsible for ``429`` status codes.

   Because we supplied the :py:class:`.UnauthorisedStatusHandler` and the :py:class:`.RateLimitStatusHandler`
   handlers first in the list, they take priority over the :py:class:`.ClientErrorStatusHandler`.
   However, if we had done the following then all ``400``-``499`` responses would be handled by the
   :py:class:`.ClientErrorStatusHandler`.

   .. literalinclude:: scripts/request/status.py
      :language: Python
      :start-after: # REORDER
      :end-before: # END

.. seealso::
   For more info on :py:class:`.StatusHandler` and how they handle each response type, see :ref:`status-guide`.


.. _request-timer:

Managing retries and backoff time
---------------------------------

Another way we can ensure a successful response is to include a retry and backoff time management strategy.

The :py:class:`.RequestHandler` provides two key mechanisms for these operations:

* The :py:attr:`.RequestHandler.wait_timer` manages the time to wait after every request whether successful or not.
  This is **object-bound** i.e. any increase to this timer affects future requests.
* The :py:attr:`.RequestHandler.retry_timer` manages the time to wait after each unsuccessful and unhandled request.
  This is **request-bound** i.e. any increase to this timer only affects the current request and not future requests.

Retries and unsuccessful backoff time
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

As an example, if we want to simply retry the same request 3 times without any backoff time in-between each request,
we can set the following:

.. literalinclude:: scripts/request/timer.py
   :language: Python
   :start-after: # ASSIGNMENT - RETRY NO TIME
   :end-before: # END

We set the ``count`` value to ``3`` for 3 retries and all other values to ``0`` to ensure there is no wait time between
these retries.

Should we wish to add some time between each retry, we can do the following:

.. literalinclude:: scripts/request/timer.py
   :language: Python
   :start-after: # ASSIGNMENT - RETRY WITH TIME
   :end-before: # END

This will now add 0.2 seconds between each unsuccessful request, waiting 0.6 seconds before the final retry.

This timer is generated as new for each new request so any increase in time
**does not carry through to future requests**.

Wait backoff time
^^^^^^^^^^^^^^^^^

We may also wish to handle wait time after all requests.
This can be useful for sensitive services that often return 'Too Many Requests' errors when making a large volume
of requests at once.

.. literalinclude:: scripts/request/timer.py
   :language: Python
   :start-after: # ASSIGNMENT - WAIT
   :end-before: # END

This timer will increase by 0.1 seconds each time it is increased up to a maximum of 1 second.

.. warning::
   The :py:class:`.RequestHandler` is not responsible for handling when this timer is increased.
   A :py:class:`.StatusHandler` should be used to increase this timer such as the :ref:`status-ratelimit`
   which will increase this timer every time a 'Too Many Requests' error is returned.

This timer is the same for each new request so any increase in time
**does carry through to future requests**.

Assignment on instantiation
^^^^^^^^^^^^^^^^^^^^^^^^^^^

As usual, we may also assign these :py:class:`.Timer` objects when we create the :py:class:`.RequestHandler` too.

.. literalinclude:: scripts/request/timer.py
   :language: Python
   :start-after: # INSTANTIATION
   :end-before: # END

.. seealso::
   For more info on the available :py:class:`.Timer` objects, see :ref:`timer-guide`.
