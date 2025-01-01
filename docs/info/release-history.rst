.. Add log for your proposed changes here.

   The versions shall be listed in descending order with the latest release first.

   Change categories:
      Added          - for new features.
      Changed        - for changes in existing functionality.
      Deprecated     - for soon-to-be removed features.
      Removed        - for now removed features.
      Fixed          - for any bug fixes.
      Security       - in case of vulnerabilities.
      Documentation  - for changes that only affected documentation and no functionality.

   Your additions should keep the same structure as observed throughout the file i.e.

      <release version>
      =================

      <one of the above change categories>
      ------------------------------------
      * <your 1st change>
      * <your 2nd change>
      ...

.. _release-history:

===============
Release History
===============

The format is based on `Keep a Changelog <https://keepachangelog.com/en>`_,
and this project adheres to `Semantic Versioning <https://semver.org/spec/v2.0.0.html>`_


1.0.8
=====

Fixed
-----
* :py:class:`.AuthorisationCodeFlow` now correctly picks up the returned state value from the redirect URL
  even if it also contains the HTTP version


1.0.7
=====

Changed
-------
* Handle no response as a retry using the retry timer in :py:class:`.RequestHandler`


1.0.6
=====

Fixed
-----
* Drop debug print statement


1.0.5
=====

Fixed
-----
* Replace ``classmethod`` + ``property`` decorators with custom :py:class:`.classproperty` decorator
  to fix issues in Python v3.13


1.0.4
=====

Fixed
-----
* Removed debug print statement


1.0.3
=====

Fixed
-----
* Bug in :py:meth:`get_iterator` causing :py:class:`.RequestInfo` objects
  to iterate its properties instead of itself

1.0.2
=====

Changed
-------
* Update upstream dependency versions


1.0.1
=====

Fixed
-----
* Typing in :py:class:`.RequestHandler`
* Missing python-dateutil dependency


1.0.0
=====

Changed
-------
* Moved :py:class:`.RequestHandler` to base of package in request.py
* Moved all :py:class:`.Timer` implementations to base of package in timer.py
* Moved all request exceptions to base of package in exception.py

Documentation
-------------
* Finalise writing guides


0.6.1
=====

Added
-----
* Raise an exception on :py:meth:`.RequestHandler.request` when called and the session is closed.

Documentation
-------------
* Expand README to complete all placeholder sections


0.6.0
=====

Changed
-------
* Rename AuthResponseHandler to :py:class:`.AuthResponse`.
  Implements MutableMapping to allow handling of response on the object directly.
* Rename AuthResponseTester to :py:class:`.AuthTester`.
  :py:meth:`.AuthTester.test` now only requires the :py:class:`.AuthResponse` for input.

Fixed
-----
* Removed bad exception condition on retry timer in :py:class:`.RequestHandler`

0.5.2
=====

Fixed
-----
* Bug when awaiting :py:class:`.Timer`.


0.5.1
=====

Changed
-------
* Removed ability to pass response to methods in :py:class:`.AuthResponseHandler`.
  Now only the stored response is used always.

Fixed
-----
* Headers not passed to response tester. Now works as expected.


0.5.0
=====

Changed
-------
* :py:class:`.Timer` now supports int and float operations.
* All cache backends no longer rely on JSON based payloads and have been made generic enough
  to support all :py:class:`.PayloadHandler` implementations.

Removed
-------
* ``value`` property on :py:class:`.Timer` in favour of using builtin ``int`` and ``float`` calls
  to get the timer value.

Documentation
-------------
* Add standard info for installing
* Expand and reformat index

0.4.0
=====

Changed
-------
* RequestSettings renamed to :py:class:`.ResponseRepositorySettings`
* :py:meth:`.ResponseRepositorySettings.get_key` now accepts all request kwargs as given by :py:class:`.RequestKwargs`.
  In addition, :py:class:`.ResponseRepository` now passes ``method``, ``url``, and ``headers``
  to :py:meth:`.ResponseRepositorySettings.get_key`
* ``factor`` renamed to ``exponent`` on power :py:class:`.Timer` implementations
* Renamed serialise method to :py:meth:`.PayloadHandler.deserialize` on :py:class:`.PayloadHandler`

Documentation
-------------
* Expanded docstrings everywhere


0.3.1
=====

Added
-----
* Implementation of __slots__ wherever it is appropriate

Changed
-------
* Expand schema data type sizes on :py:class:`.SQLiteTable` repository
* Rename repository RequestSettings to :py:class:`.ResponseRepositorySettings`


0.3.0
=====

Changed
-------
* Rename exceptions: AIORequests... -> AIORequestful...
* Rename references of payload as ``data`` to ``payload``
* Abstract and implement response handling, request timer handling, and payload handling
  in new :py:mod:`.request` and :py:mod:`.response` modules.
* Migrate all resources relating to requests and responses to relevant modules.

Removed
-------
* MethodInput enum in favour of http.HTTPMethod


0.2.1
=====

Fixed
-----
* Client ID not being passed to :py:meth:`.ClientCredentialsFlow.create` and :py:meth:`.AuthorisationCodeFlow.create`
  from relevant create_with_encoded_credentials methods. Now passed correctly.


0.2.0
=====

Added
-----
* OAuth2 Client Credentials flow implementation
* OAuth2 Authorization Code with PKCE flow implementation
* Basic user/password authorisation implementation
* :py:class:`.RequestKwargs` TypedDict

Changed
-------
* Create abstraction for authorise module and convert implementation of OAuth2 Authorization Code flow
  to match this interface


0.1.1
=====

Changed
-------
* Method as str for logging on :py:class:`.RequestHandler`


0.1.0
=====

Initial release! 🎉
