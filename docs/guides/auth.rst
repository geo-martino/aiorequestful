.. _auth-guide:

Authorising requests
====================

This package provides a simple-to-use framework for authorising access to a HTTP service, such as a REST API.

Basic usage
-----------

All :py:class:`.Authoriser` implementations can be used the same simple way.

.. literalinclude:: scripts/auth/core.py
   :language: Python

These calls will handle the authorisation process from start to finish, returning the headers necessary to send
authorised requests.

.. seealso::
   This package implements a some common authorisation flows as shown below, though you may wish to
   :ref:`extend this functionality <auth-custom>`.

Basic Authorisation
-------------------




.. _auth-custom:

Writing an :py:class:`.Authoriser`
----------------------------------