.. _status-guide:

Handling error responses
========================

The :py:mod:`.response.status` module provides tools to handle error responses in such a way that future requests
can be made successfully seamlessly.

These objects are designed to be used exclusively with the :py:class:`.RequestHandler`.


Basic usage
-----------

A :py:class:`.StatusHandler` should not be used directly to handle responses. The aim of a :py:class:`.StatusHandler`
is to be passed to the :py:class:`.RequestHandler` to handle responses there.

Each :py:class:`.StatusHandler` should be built to accept the args and kwargs as per the
:py:class:`.RequestHandler` method quoted below.

.. literalinclude:: /../aiorequestful/request.py
   :language: Python
   :pyobject: RequestHandler._handle_response
   :dedent: 4

The status handler will return ``True`` for a handled response, and ``False`` if it could not handle the response.
It will raise a :py:class:`.StatusHandlerError` if the status code of the response does not match the status code
of the response.

.. seealso::
   For more info on how to pass :py:class:`.StatusHandler` objects to the :py:class:`.RequestHandler`,
   see :ref:`request-status`.


Supported status handlers
-------------------------

The following is a list of each implemented status handler included in this module with excerpts from their
source code showing the supported status codes and the :py:meth:`.StatusHandler.handle` logic they implement.

.. seealso::
   You may wish to :ref:`extend this functionality <status-custom>`.

:py:class:`.ClientErrorStatusHandler`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. literalinclude:: /../aiorequestful/response/status.py
      :language: Python
      :pyobject: ClientErrorStatusHandler.status_codes
      :dedent: 4

.. literalinclude:: /../aiorequestful/response/status.py
      :language: Python
      :pyobject: ClientErrorStatusHandler.handle
      :dedent: 4

:py:class:`.UnauthorisedStatusHandler`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. literalinclude:: /../aiorequestful/response/status.py
      :language: Python
      :pyobject: UnauthorisedStatusHandler.status_codes
      :dedent: 4

.. literalinclude:: /../aiorequestful/response/status.py
      :language: Python
      :pyobject: UnauthorisedStatusHandler.handle
      :dedent: 4

.. _status-ratelimit:

:py:class:`.RateLimitStatusHandler`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. literalinclude:: /../aiorequestful/response/status.py
      :language: Python
      :pyobject: RateLimitStatusHandler.status_codes
      :dedent: 4

.. literalinclude:: /../aiorequestful/response/status.py
      :language: Python
      :pyobject: RateLimitStatusHandler.handle
      :dedent: 4


.. _status-custom:

Writing a :py:class:`.StatusHandler`
------------------------------------

To implement a :py:class:`.StatusHandler`, you will need to implement the abstract methods as shown below.

.. literalinclude:: /../aiorequestful/response/status.py
   :language: Python
   :pyobject: StatusHandler

As an example, the following implements the :py:class:`.UnauthorisedStatusHandler`.

.. literalinclude:: /../aiorequestful/response/status.py
   :language: Python
   :pyobject: UnauthorisedStatusHandler
