.. _guide-timer:

Timers
======

A :py:class:`.Timer` simply stores a ``float`` or ``int`` value and increments it based on some mathematical formula.
Sleep operations can then be called on the :py:class:`.Timer` to pause operation for the number of seconds specified
by the value of the :py:class:`.Timer`.

The main motivation for this is to provide a flexible framework for managing retries and backoff for the
:py:class:`.RequestHandler`.

.. seealso::
   See :ref:`request-timer` for more info in how a :py:class:`.Timer` can be used with
   :py:class:`.RequestHandler` to handle retries and backoff.

This page gives an overview of some of the :py:class:`.Timer` implementations provided by this package,
with info on how to implement your own.

Basic usage
-----------

.. literalinclude:: scripts/timer.py
   :language: Python
   :start-after: # PART 0
   :end-before: # PART 1

:py:class:`.CountTimer`
-----------------------

Provides an abstract implementation for managing a number of :py:class:`.Timer` value increases specified
by a given ``count`` value.

:py:class:`.StepCountTimer`
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Increases timer value by a given ``step`` amount a distinct number of times.

.. literalinclude:: scripts/timer.py
   :language: Python
   :start-after: # PART 1
   :end-before: # PART 2

:py:class:`.GeometricCountTimer`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Increases timer value by multiplying the current value by a given ``factor`` a distinct number of times.

.. literalinclude:: scripts/timer.py
   :language: Python
   :start-after: # PART 2
   :end-before: # PART 3

:py:class:`.PowerCountTimer`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Increases timer value by raising the current value to a given ``exponent`` a distinct number of times.

.. literalinclude:: scripts/timer.py
   :language: Python
   :start-after: # PART 3
   :end-before: # PART 4

:py:class:`.CeilingTimer`
-------------------------

Provides an abstract implementation for managing :py:class:`.Timer` value increases up to a specified ``final`` value.

:py:class:`.StepCeilingTimer`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Increases timer value by a given ``step`` amount until a maximum value is reached.

.. literalinclude:: scripts/timer.py
   :language: Python
   :start-after: # PART 4
   :end-before: # PART 5

:py:class:`.GeometricCeilingTimer`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Increases timer value by multiplying the current value by a given ``factor`` until a maximum value is reached.

.. literalinclude:: scripts/timer.py
   :language: Python
   :start-after: # PART 5
   :end-before: # PART 6

:py:class:`.PowerCeilingTimer`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Increases timer value by raising the current value to a given ``exponent`` until a maximum value is reached.

.. literalinclude:: scripts/timer.py
   :language: Python
   :start-after: # PART 6

Writing a :py:class:`.Timer`
----------------------------

To implement a :py:class:`.Timer`, you will need to implement the abstract methods as below.

.. literalinclude:: /../aiorequestful/timer.py
   :language: Python
   :pyobject: Timer

As an example, the following implements the :py:class:`.StepCountTimer`.

.. literalinclude:: /../aiorequestful/timer.py
   :language: Python
   :pyobject: CountTimer

.. literalinclude:: /../aiorequestful/timer.py
   :language: Python
   :pyobject: StepCountTimer
