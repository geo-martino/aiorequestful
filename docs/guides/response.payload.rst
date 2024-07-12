.. _payload-guide:

Handling payload data
=====================

This package provides a basic interface and implementations for handling payload data returned by a HTTP request.

Basic usage
-----------

The :py:class:`.PayloadHandler` transforms data returned by a HTTP request to a usable python object.

.. literalinclude:: scripts/response/payload_core.py
   :language: Python

These two methods should accept a variety of input types as below where T is the supported output type of
the :py:class:`.PayloadHandler`.
Crucially, :py:meth:`.PayloadHandler.deserialize` should accept the ``ClientResponse`` as returned by
the ``aiohttp`` package.

.. literalinclude:: /../aiorequestful/response/payload.py
   :language: Python
   :pyobject: PayloadHandler.serialize
   :dedent: 4

.. literalinclude:: /../aiorequestful/response/payload.py
   :language: Python
   :pyobject: PayloadHandler.deserialize
   :dedent: 4

.. seealso::
   This package implements a few common payload data types as shown below, though you may wish to
   :ref:`extend this functionality <payload-custom>`.

.. seealso::
   For more info on how to pass a :py:class:`.PayloadHandler` to the :py:class:`.RequestHandler`,
   see :ref:`request-payload`.

:py:class:`.StringPayloadHandler`
---------------------------------

Converts payload data to ``str`` objects.

.. literalinclude:: scripts/response/payload.py
   :language: Python
   :start-after: # STRING
   :end-before: # END

:py:class:`.JSONPayloadHandler`
-------------------------------

Converts payload data to ``dict`` objects.

.. literalinclude:: scripts/response/payload.py
   :language: Python
   :start-after: # JSON
   :end-before: # END

.. _payload-custom:

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



