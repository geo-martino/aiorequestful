.. _auth-guide:

Authorising requests
====================

The :py:mod:`.auth` module provides a framework and various implementations for authorising access to a HTTP service,
such as a REST API.


Basic usage
-----------

All :py:class:`.Authoriser` implementations can be used in the same way.

.. literalinclude:: scripts/auth/core.py
   :language: Python
   :start-after: # BASIC
   :end-before: # END

All implementations of :py:class:`.Authoriser` will accept a ``service_name`` which is a just a simple name to refer
to the service. This will only be used in logging and exception messages.

The calls in the ``auth`` function will handle the authorisation process from start to finish,
returning the headers necessary to send authorised requests.

.. seealso::
   This module implements some common authorisation flows as shown below, though you may wish to
   :ref:`extend this functionality <auth-custom>`.


Basic Authorisation
-------------------

Authoriser with a service using a username and password (if necessary).
You may also provide an optional encoding identifier to define how the credentials should be encoded before
applying Base64 encoding.

.. literalinclude:: scripts/auth/basic.py
   :language: Python
   :start-after: # USER/PASSWORD
   :end-before: # END


:py:class:`.OAuth2Authoriser`
-----------------------------

Authorise with a service that implements an OAuth2 authorisation flow.

.. note::
   The `OAuth2 framework specification <https://auth0.com/docs/authenticate/protocols/oauth>`_
   provides many possible flows for authorising depending on the use case.
   Check which flow the HTTP service you are trying to access allows you to use and use the appropriate one for
   your use case.

.. seealso::
   These implementations make heavy use of the :ref:`utilities <auth-utils>` below so do familiarise yourself with
   those to take full advantage of the authorisers.

All :py:class:`.OAuth2Authoriser` implementations may take the following arguments on initialisation.

.. literalinclude:: scripts/auth/oauth2.py
   :language: Python
   :start-after: # BASE
   :end-before: # END

.. seealso::
   Check out the :ref:`auth-utils-request`, :ref:`auth-utils-response`, and :ref:`auth-utils-tester` sections
   for more info on how to instantiate these parameters.

:py:class:`.ClientCredentialsFlow`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Implements the
`Client Credentials flow <https://auth0.com/docs/get-started/authentication-and-authorization-flow/client-credentials-flow>`_
as per the OAuth2 specification.

.. literalinclude:: scripts/auth/oauth2.py
   :language: Python
   :start-after: # CLIENT CREDENTIALS - INIT
   :end-before: # END

To simplify the creation process, you may use the :py:meth:`.ClientCredentialsFlow.create` method to
automatically generate some of the utility objects from the given parameters.

.. literalinclude:: scripts/auth/oauth2.py
   :language: Python
   :start-after: # CLIENT CREDENTIALS - CREATE
   :end-before: # END

If the service you are accessing requires you send encoded credentials as part of the authorisation process,
you may also use the :py:meth:`.ClientCredentialsFlow.create_with_encoded_credentials` method.
This generates utility objects which send the credentials as headers in Base64 encoding i.e.

.. code-block:: python

   {'Authorization': 'Basic <base64 encoded client_id:client_secret>'}

.. literalinclude:: scripts/auth/oauth2.py
   :language: Python
   :start-after: # CLIENT CREDENTIALS - CREATE ENCODED
   :end-before: # END

:py:class:`.AuthorisationCodeFlow`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Implements the
`Authorization Code flow <https://auth0.com/docs/get-started/authentication-and-authorization-flow/authorization-code-flow>`_
as per the OAuth2 specification.

.. literalinclude:: scripts/auth/oauth2.py
   :language: Python
   :start-after: # AUTHORISATION CODE - INIT
   :end-before: # END

To simplify the creation process, you may use the :py:meth:`.AuthorisationCodeFlow.create` method to
automatically generate some of the utility objects from the given parameters.

.. literalinclude:: scripts/auth/oauth2.py
   :language: Python
   :start-after: # AUTHORISATION CODE - CREATE
   :end-before: # END

If the service you are accessing requires you send encoded credentials as part of the authorisation process,
you may also use the :py:meth:`.AuthorisationCodeFlow.create_with_encoded_credentials` method.
This generates utility objects which send the credentials as headers in Base64 encoding i.e.

.. code-block:: python

   {'Authorization': 'Basic <base64 encoded client_id:client_secret>'}

.. literalinclude:: scripts/auth/oauth2.py
   :language: Python
   :start-after: # AUTHORISATION CODE - CREATE ENCODED
   :end-before: # END

:py:class:`.AuthorisationCodePKCEFlow`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Implements the
`Authorization Code with PKCE flow <https://auth0.com/docs/get-started/authentication-and-authorization-flow/authorization-code-flow-with-pkce>`_
as per the OAuth2 specification.

.. literalinclude:: scripts/auth/oauth2.py
   :language: Python
   :start-after: # AUTHORISATION CODE WITH PKCE - INIT
   :end-before: # END

To simplify the creation process, you may use the :py:meth:`.AuthorisationCodePKCEFlow.create` method to
automatically generate some of the utility objects from the given parameters.

.. literalinclude:: scripts/auth/oauth2.py
   :language: Python
   :start-after: # AUTHORISATION CODE WITH PKCE - CREATE
   :end-before: # END

If the service you are accessing requires you send encoded credentials as part of the authorisation process,
you may also use the :py:meth:`.AuthorisationCodePKCEFlow.create_with_encoded_credentials` method.
This generates utility objects which send the credentials as headers in Base64 encoding i.e.

.. code-block:: python

   {'Authorization': 'Basic <base64 encoded client_id:client_secret>'}

.. literalinclude:: scripts/auth/oauth2.py
   :language: Python
   :start-after: # AUTHORISATION CODE WITH PKCE - CREATE ENCODED
   :end-before: # END

.. _auth-utils:


Utilities
---------

The :py:mod:`.auth.utils` module provides various utilities to aid in automatic authorisation depending on the flow.

.. _auth-utils-request:

:py:class:`.AuthRequest`
^^^^^^^^^^^^^^^^^^^^^^^^

Simply a wrapper for an aiohttp
`request <https://docs.aiohttp.org/en/stable/client_reference.html#aiohttp.ClientSession.request>`_.
Stores the kwargs necessary to make a request. This allows the :py:class:`.Authoriser` to make the request as required.

We may provide the request kwargs on initialisation and execute with :py:meth:`.AuthRequest.request`.

.. literalinclude:: scripts/auth/utils.py
   :language: Python
   :start-after: # AUTH REQUEST - BASIC
   :end-before: # END

We may also wish to add temporary parameters to the request should we wish to add sensitive or other temporary
information to the request.

.. literalinclude:: scripts/auth/utils.py
   :language: Python
   :start-after: # AUTH REQUEST - TEMP PARAMS
   :end-before: # END

.. _auth-utils-response:

:py:class:`.AuthResponse`
^^^^^^^^^^^^^^^^^^^^^^^^^

Stores a converted JSON response returned from a service, providing a facade for interacting with the values in
the response directly and indirectly.

Crucially, it provides the :py:attr:`.AuthResponse.token` and :py:attr:`.AuthResponse.headers` properties
which manage extraction of this information from the response to make an authorised request with.

.. literalinclude:: scripts/auth/utils.py
   :language: Python
   :start-after: # AUTH RESPONSE - BASIC
   :end-before: # END

You may also configure additional headers that are required for successful, authorised requests.
Equally, if your service does not return the ``token_type`` key, you may specify a fallback default too.

.. literalinclude:: scripts/auth/utils.py
   :language: Python
   :start-after: # AUTH RESPONSE - ADVANCED
   :end-before: # END

You may also enrich a response to add a UNIX timestamp value for the ``granted_at`` and ``expires_at`` times
for the token.

.. warning::
   To add an ``expires_at`` time to the response, the response must return with a value for the ``expires_in`` key.

.. literalinclude:: scripts/auth/utils.py
   :language: Python
   :start-after: # AUTH RESPONSE - ENRICH
   :end-before: # END

.. _auth-utils-tester:

:py:class:`.AuthTester`
^^^^^^^^^^^^^^^^^^^^^^^

Sets up a series of tests to check the validity of a response.

.. literalinclude:: scripts/auth/utils.py
   :language: Python
   :start-after: # AUTH TESTER - BASIC
   :end-before: # END

* The ``request`` is a request that is sent using the headers generated by the :py:class:`.AuthResponse`.
* The ``response_test`` tests the response retrieved from this ``request``
* The ``max_expiry`` is the maximum allowed remaining time on the token in seconds.
  This is calculated during the test as the difference  between the current time and the ``expires_at``  time.
  The test fails when this value is below the ``max_expiry`` time.

.. _auth-utils-socket:

:py:class:`.SocketHandler`
^^^^^^^^^^^^^^^^^^^^^^^^^^

Handles managing a socket to open to listen for callback data.
Useful for authorisation flows which return an authorisation code via a redirect URL.

.. literalinclude:: scripts/auth/utils.py
   :language: Python
   :start-after: # SOCKET HANDLER - BASIC
   :end-before: # END


.. _auth-custom:

Writing an :py:class:`.Authoriser`
----------------------------------

To implement an :py:class:`.Authoriser`, you will need to implement the abstract methods as shown below.

.. literalinclude:: /../aiorequestful/auth/base.py
   :language: Python
   :pyobject: Authoriser

As an example, the following implements the :py:class:`.BasicAuthoriser`.

.. literalinclude:: /../aiorequestful/auth/basic.py
   :language: Python
   :pyobject: BasicAuthoriser
