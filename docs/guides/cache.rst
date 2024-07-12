.. _cache-guide:

Caching responses
=================

The :py:mod:`.cache` module provides a framework and various implementations for storing responses
to common backend data stores.

.. seealso::
   This module implements some common backend data stores, though you may wish to
   :ref:`extend this functionality <cache-custom>`.


Core concepts and usage
-----------------------

There are three classes that are key to setting up and managing the backend.

:py:class:`.ResponseRepositorySettings`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Stores the settings which define where and how a response is stored in the cache.

.. literalinclude:: scripts/cache/backend/settings.py
   :language: Python
   :start-after: # BASIC
   :end-before: # END

You may also define a handler to transform the data before storing it in the cache.
If not defined, the payload data will be extracted and stored as simple text data.

.. literalinclude:: scripts/cache/backend/settings.py
   :language: Python
   :start-after: # PAYLOAD
   :end-before: # END

However, the :py:class:`.ResponseRepositorySettings` class is actually an abstract class and none of the above code
will actually run.

In order to actually instantiate our settings, we need to implement the :py:class:`.ResponseRepositorySettings`
interface by defining the following:

* the ``key`` that can be used to identify a response in the cache repository
* the names of the ``fields`` of each of these keys
* how we get the ``name`` of the repository from the payload data

i.e. you will need to implement the following interface:

.. literalinclude:: /../aiorequestful/cache/backend/base.py
   :language: Python
   :pyobject: ResponseRepositorySettings

As an example, see below for extracting data from a
`Spotify Web API <https://developer.spotify.com/documentation/web-api/reference/get-track>`_ response.

.. literalinclude:: scripts/cache/backend/base.py
   :language: Python
   :start-after: # SETTINGS
   :end-before: # END

Here we see that the :py:attr:`.ResponseRepositorySettings.fields` are defined as the ``id`` and the ``version``.
These are the fields required to identify a unique response in the repository.

In the :py:meth:`.ResponseRepositorySettings.get_key` method, we extract the ``id`` and the ``version``
and return them.
We also return ``None, None`` for any request that is not a ``GET`` request, or if the URL does not
match the expected format.
This will force our cache to not be able to identify the response and therefore not cache it.

We also define the :py:meth:`.ResponseRepositorySettings.get_name` method to extract the ``name`` of the repository
from a response's payload.

:py:class:`.ResponseRepository`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Once we've defined our :py:class:`.ResponseRepositorySettings`, we can use these to define a
:py:class:`.ResponseRepository`. This represents a store of data relating to the given settings.

.. literalinclude:: scripts/cache/backend/base.py
   :language: Python
   :start-after: # REPOSITORY - INIT
   :end-before: # END

The ``expire`` parameter here defines how long after caching a response it will remain valid and retrievable in the
cache.
For example, if we cache a response today and make the same request with this cache in 1 week, we will
retrieve the cached response.
However, if we make the same request in 3 weeks, the HTTP request will be made without retrieving the cached response.

Below is an example on how we might use this cache to handle caching our responses.

.. literalinclude:: scripts/cache/backend/base.py
   :language: Python
   :start-after: # REPOSITORY - USAGE
   :end-before: # END

Here we create the repository and manage storing responses manually. However, it is advised that we use a
:py:class:`.ResponseCache` to manage our repositories.

:py:class:`.ResponseCache`
^^^^^^^^^^^^^^^^^^^^^^^^^^

Manages a collection of repositories along with a connection to the backend.

.. literalinclude:: scripts/cache/backend/base.py
   :language: Python
   :start-after: # CACHE - INIT
   :end-before: # END

Now we can use the cache to help manage the creation of repositories.

.. literalinclude:: scripts/cache/backend/base.py
   :language: Python
   :start-after: # CACHE - SETUP
   :end-before: # END

.. seealso::
   Here we assign the :py:class:`.PayloadHandler` for each repository manually.
   However, as we will usually use the :py:class:`.ResponseCache` as part of the :py:class:`.RequestHandler`,
   we do not need to add the :py:class:`.PayloadHandler` here as the :py:class:`.RequestHandler` will manage
   that for us.

   For more info on how this can be used, see :ref:`request-payload`.

.. warning::
   By calling :py:meth:`.ResponseCache.create_repository`, we are only defining the repository on the
   :py:class:`.ResponseCache` object and have not actually created the repository on the backend.

   To create the repository on the backend, we will need to connect to the cache and then create them.
   This is most easily achieved by entering the context of the :py:class:`.ResponseCache`

   .. literalinclude:: scripts/cache/backend/base.py
      :language: Python
      :start-after: # CACHE - USAGE
      :end-before: # END


Cached sessions and responses
-----------------------------

To aid in a seamless usage of cached and non-cached setups when using the :py:class:`.RequestHandler`,
the :py:mod:`.cache` module also provides a :py:class:`.CachedSession` and a :py:class:`.CachedResponse` implementation.


:py:class:`.CachedResponse`
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Takes a ``ClientRequest`` and ``payload`` to mock a
`ClientResponse <https://docs.aiohttp.org/en/stable/client_reference.html#aiohttp.ClientResponse>`_.
Allows for seamless usage of cached responses as if they were returned by a genuine HTTP request.
You can use :py:class:`.CachedResponse` in exactly the same way you would a regular
`ClientResponse <https://docs.aiohttp.org/en/stable/client_reference.html#aiohttp.ClientResponse>`_.

.. literalinclude:: scripts/cache/response.py
   :language: Python
   :start-after: # BASIC
   :end-before: # END

:py:class:`.CachedSession`
^^^^^^^^^^^^^^^^^^^^^^^^^^

Takes a :py:class:`.ResponseCache` to mock a
`ClientSession <https://docs.aiohttp.org/en/stable/client_reference.html#aiohttp.ClientSession>`_.
The :py:class:`.CachedSession` will always attempt to call the cache first before falling back to making an actual
HTTP request to get the response.
You can use :py:class:`.CachedSession` in exactly the same way you would a regular
`ClientSession <https://docs.aiohttp.org/en/stable/client_reference.html#aiohttp.ClientSession>`_.

.. literalinclude:: scripts/cache/session.py
   :language: Python
   :start-after: # BASIC
   :end-before: # END


SQLite
------

:py:class:`.SQLiteTable`
^^^^^^^^^^^^^^^^^^^^^^^^

In addition to the available kwargs for the base :py:class:`.ResponseRepository`, we also need to provide a
`Connection <https://aiosqlite.omnilib.dev/en/stable/api.html#aiosqlite.Connection>`_ to the database.

.. literalinclude:: scripts/cache/backend/sqlite.py
   :language: Python
   :start-after: # REPOSITORY
   :end-before: # END

:py:class:`.SQLiteCache`
^^^^^^^^^^^^^^^^^^^^^^^^

The implementation provides a variety of standard database connections to aid in the quick set up of an
SQLite cache backend.

While we can instantiate the SQLiteCache directly by providing a ``connector`` to a
`Connection <https://aiosqlite.omnilib.dev/en/stable/api.html#aiosqlite.Connection>`_ object...

.. literalinclude:: scripts/cache/backend/sqlite.py
   :language: Python
   :start-after: # CACHE - INIT
   :end-before: # END

...it is preferable to use one of the class methods for connecting to an SQLite database backend.

.. literalinclude:: scripts/cache/backend/sqlite.py
   :language: Python
   :start-after: # CACHE - CLASS METHOD INIT
   :end-before: # END


.. _cache-custom:

Writing a :py:class:`.ResponseRepository`
-----------------------------------------

To implement a :py:class:`.ResponseRepository`, you will need to implement the abstract methods as shown below.

.. literalinclude:: /../aiorequestful/cache/backend/base.py
   :language: Python
   :pyobject: ResponseRepository

As an example, the following implements the :py:class:`.SQLiteTable`.

.. literalinclude:: /../aiorequestful/cache/backend/sqlite.py
   :language: Python
   :pyobject: SQLiteTable


Writing a :py:class:`.ResponseCache`
------------------------------------

To implement a :py:class:`.ResponseCache`, you will need to implement the abstract methods as shown below.

.. literalinclude:: /../aiorequestful/cache/backend/base.py
   :language: Python
   :pyobject: ResponseCache

As an example, the following implements the :py:class:`.SQLiteCache`.

.. literalinclude:: /../aiorequestful/cache/backend/sqlite.py
   :language: Python
   :pyobject: SQLiteCache