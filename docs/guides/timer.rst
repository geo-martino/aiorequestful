.. _timer-guide:

Timers
======

A :py:class:`.Timer` found in the :py:mod:`.timer` module simply stores a ``float`` or ``int`` value and increments
it based on some mathematical formula.
Sleep operations can then be called on the :py:class:`.Timer` to pause operation for the number of seconds specified
by the value of the :py:class:`.Timer`.

The main motivation for this is to provide a flexible framework for managing retries and backoff for the
:py:class:`.RequestHandler`.

.. seealso::
   See :ref:`request-timer` for more info in how a :py:class:`.Timer` can be used with
   :py:class:`.RequestHandler` to handle retries and backoff.

This page gives an overview of some of the :py:class:`.Timer` implementations provided in this module,
with info on how to implement your own.


Basic usage
-----------

.. literalinclude:: scripts/timer/core.py
   :language: Python
   :start-after: # BASIC
   :end-before: # END

.. seealso::
   This module implements a few basic timing formulae as shown below, though you may wish to
   :ref:`extend this functionality <timer-custom>`.


:py:class:`.CountTimer`
-----------------------

Provides an abstract implementation for managing a number of :py:class:`.Timer` value increases specified
by a given ``count`` value.

:py:class:`.StepCountTimer`
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Increases the timer value by a given ``step`` amount a distinct number of times.

.. literalinclude:: scripts/timer/timer.py
   :language: Python
   :start-after: # StepCountTimer
   :end-before: # END

:py:class:`.GeometricCountTimer`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Increases the timer value by multiplying the current value by a given ``factor`` a distinct number of times.

.. literalinclude:: scripts/timer/timer.py
   :language: Python
   :start-after: # GeometricCountTimer
   :end-before: # END

:py:class:`.PowerCountTimer`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Increases the timer value by raising the current value to a given ``exponent`` a distinct number of times.

.. literalinclude:: scripts/timer/timer.py
   :language: Python
   :start-after: # PowerCountTimer
   :end-before: # END


:py:class:`.CeilingTimer`
-------------------------

Provides an abstract implementation for managing :py:class:`.Timer` value increases up to a specified ``final`` value.

:py:class:`.StepCeilingTimer`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Increases the timer value by a given ``step`` amount until a maximum value is reached.

.. literalinclude:: scripts/timer/timer.py
   :language: Python
   :start-after: # StepCeilingTimer
   :end-before: # END

:py:class:`.GeometricCeilingTimer`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Increases the timer value by multiplying the current value by a given ``factor`` until a maximum value is reached.

.. literalinclude:: scripts/timer/timer.py
   :language: Python
   :start-after: # GeometricCeilingTimer
   :end-before: # END

:py:class:`.PowerCeilingTimer`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Increases the timer value by raising the current value to a given ``exponent`` until a maximum value is reached.

.. literalinclude:: scripts/timer/timer.py
   :language: Python
   :start-after: # PowerCeilingTimer
   :end-before: # END


.. _timer-custom:

Writing a :py:class:`.Timer`
----------------------------

To implement a :py:class:`.Timer`, you will need to implement the abstract methods as shown below.

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
