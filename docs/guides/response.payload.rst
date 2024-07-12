.. _guide-payload:

Handling payload data
=====================

This package provides a basic interface and implementations for handling payload data returned by a HTTP request.

Basic usage
-----------

The :py:class:`.PayloadHandler` transforms data returned by a HTTP request to a usable python object.

.. literalinclude:: scripts/response/payload.py
   :language: Python
   :start-after: # PART 0
   :end-before: # PART 1

These two methods should accept a variety of input types as below where T is the supported output type of
the :py:class:`.PayloadHandler`.
Crucially, :py:meth:`.PayloadHandler.deserialize` should accept the ``ClientResponse`` as returned by
the ``aiohttp`` package.

.. literalinclude:: /../aiorequestful/response/payload.py
   :language: Python
   :pyobject: PayloadHandler.serialize

.. literalinclude:: /../aiorequestful/response/payload.py
   :language: Python
   :pyobject: PayloadHandler.deserialize

.. seealso::
   For more info on how to pass a :py:class:`.PayloadHandler` to the :py:class:`.RequestHandler`,
   see :ref:`request-payload`.

:py:class:`.StringPayloadHandler`
---------------------------------

Converts payload data to ``str`` objects.

.. literalinclude:: scripts/response/payload.py
   :language: Python
   :start-after: # PART 1
   :end-before: # PART 2

:py:class:`.JSONPayloadHandler`
-------------------------------

Converts payload data to ``dict`` objects.

.. literalinclude:: scripts/response/payload.py
   :language: Python
   :start-after: # PART 2

Writing a :py:class:`.PayloadHandler`
-------------------------------------

To implement a :py:class:`.PayloadHandler`, you will need to implement the abstract methods as below.

.. literalinclude:: /../aiorequestful/response/payload.py
   :language: Python
   :pyobject: PayloadHandler

As an example, the following implements the :py:class:`.JSONPayloadHandler`.

.. literalinclude:: /../aiorequestful/response/payload.py
   :language: Python
   :pyobject: JSONPayloadHandler



