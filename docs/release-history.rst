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
  in new ``request`` and ``response`` modules.
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
