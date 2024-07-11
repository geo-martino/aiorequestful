.. _installation:

Installation
------------

Install through pip using one of the following commands:

.. code-block:: bash

   pip install aiorequestful
   # or
   python -m pip install aiorequestful

This package has various optional dependencies for optional functionality.
Should you wish to take advantage of some or all of this functionality, install the optional dependencies as follows:

.. code-block:: bash

   pip install aiorequestful[all]  # installs all optional dependencies

   pip install aiorequestful[sqlite]  # dependencies for working with a SQLite cache backend

   # or you may install any combination of these e.g.
   pip install aiorequestful[sqlite,test]
