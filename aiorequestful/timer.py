"""
Implementations to handle timers on the :py:class:`.RequestHandler`.

Includes various time incremental operations to manage increasing of time between requests
with various mathematical formulae.

Useful to handle backoff for requests on sensitive HTTP services
which often return a '429 - Too Many Requests' status.
"""
import asyncio
import functools
import itertools
from abc import ABC, ABCMeta, abstractmethod
from asyncio import sleep
from collections.abc import Generator
from copy import deepcopy
from typing import SupportsInt, SupportsFloat

from aiorequestful.types import Number


@functools.total_ordering
class Timer(SupportsInt, SupportsFloat, ABC):
    """
    Base interface for all timers.

    :param initial: The starting value to use.
    """

    __slots__ = ("_initial", "_value", "_counter")

    @property
    def initial(self) -> Number:
        """The initial starting timer value in seconds."""
        return self._initial

    @property
    @abstractmethod
    def final(self) -> Number | None:
        """The maximum possible timer value in seconds."""
        raise NotImplementedError

    @property
    @abstractmethod
    def total(self) -> Number | None:
        """The sum of all possible timer values in seconds."""
        raise NotImplementedError

    @property
    @abstractmethod
    def total_remaining(self) -> Number | None:
        """The sum of all possible remaining timer values in seconds not including the current value."""
        raise NotImplementedError

    @property
    @abstractmethod
    def count(self) -> int | None:
        """The total amount of times this timer can be increased."""
        raise NotImplementedError

    @property
    def counter(self) -> int | None:
        """The number of times this timer has been increased."""
        return self._counter

    @property
    def count_remaining(self) -> int | None:
        """The remaining number of times this timer can be increased."""
        if self.count is None:
            return None
        return self.count - self.counter

    @property
    @abstractmethod
    def can_increase(self) -> bool:
        """Check whether this timer can be increased"""
        raise NotImplementedError

    def __init__(self, initial: Number = 0):
        self._initial = initial
        self._value = initial
        self._counter = 0

    def __int__(self):
        return int(self._value)

    def __float__(self):
        return float(self._value)

    def __eq__(self, other: Number):
        return self._value == other

    def __lt__(self, other: Number):
        return self._value < other

    def __round__(self, n: int = None) -> float:
        return round(float(self._value), n)

    def __await__(self) -> Generator[None, None, None]:
        """Asynchronously sleep for the current time set for this timer."""
        return asyncio.sleep(self._value).__await__()

    def __call__(self) -> None:
        """Sleep for the current time set for this timer."""
        return self.wait()

    def __deepcopy__(self, memo: dict):
        cls = self.__class__
        obj = cls.__new__(cls)

        memo[id(self)] = obj
        slots = itertools.chain.from_iterable(getattr(c, '__slots__', []) for c in cls.__mro__)
        for key in slots:
            setattr(obj, key, deepcopy(getattr(self, key), memo))

        obj.reset()
        return obj

    @abstractmethod
    def increase(self) -> bool:
        """
        Increase the timer value.

        :return: True if timer was increased, False if not.
        """
        raise NotImplementedError

    def reset(self) -> None:
        """Reset the timer to its initial settings."""
        self._value = self._initial
        self._counter = 0

    def wait(self) -> None:
        """Sleep for the current time set for this timer."""
        sleep(self._value)


###########################################################################
## Count timers
###########################################################################
class CountTimer(Timer, metaclass=ABCMeta):
    """
    Abstract implementation of a :py:class:`Timer` which will increment a maximum number of times.

    :param initial: The starting value to use.
    :param count: The amount of times to increase the value.
    """

    __slots__ = ("_count",)

    @property
    def count(self):
        return self._count

    @property
    def can_increase(self) -> bool:
        return self.count is None or isinstance(self.count, int) and self.counter < self.count

    def __init__(self, initial: Number = 1, count: int = None):
        super().__init__(initial=initial)
        self._count = count


class StepCountTimer(CountTimer):
    """
    Increases timer value by a given ``step`` amount a distinct number of times.

    :param initial: The starting value to use.
    :param count: The amount of times to increase the value.
    :param step: The amount to increase the value by for each value increase.
    """

    __slots__ = ("_step",)

    @property
    def final(self):
        if self.count is None:
            return
        return self.initial + (self.step * self.count)

    @property
    def total(self):
        if self.count is None:
            return
        return sum(self.initial + self.step * i for i in range(self.count + 1))

    @property
    def total_remaining(self):
        if self.count is None:
            return
        return sum(float(self) + self.step * i for i in range(self.count_remaining + 1)) - float(self)

    @property
    def step(self) -> Number:
        """The amount to increase the timer value by in seconds."""
        return self._step

    def __init__(self, initial: Number = 0, count: int = None, step: Number = 1):
        super().__init__(initial=initial, count=count)
        self._step = step

    def increase(self) -> bool:
        if not self.can_increase:
            return False

        self._value += self.step
        self._counter += 1
        return True


class GeometricCountTimer(CountTimer):
    """
    Increases timer value by multiplying the current value by a given ``factor`` a distinct number of times.

    :param initial: The starting value to use.
    :param count: The amount of times to increase the value.
    :param factor: The amount to multiply the current value by for each value increase.
    """

    __slots__ = ("_factor",)

    @property
    def final(self):
        if self.count is None:
            return
        return self.initial * self.factor ** self.count

    @property
    def total(self):
        if self.count is None:
            return
        return sum(
            itertools.accumulate(range(1, self.count + 1), lambda s, _: s * self.factor, initial=self.initial)
        )

    @property
    def total_remaining(self):
        if self.count is None:
            return
        return sum(
            itertools.accumulate(range(self.count_remaining), lambda s, _: s * self.factor, initial=float(self))
        ) - float(self)

    @property
    def factor(self) -> Number:
        """The amount to multiply the timer value by in seconds."""
        return self._factor

    def __init__(self, initial: Number = 1, count: int = None, factor: Number = 2):
        super().__init__(initial=initial, count=count)
        self._factor = factor

    def increase(self) -> bool:
        if not self.can_increase:
            return False

        self._value *= self.factor
        self._counter += 1
        return True


class PowerCountTimer(CountTimer):
    """
    Increases timer value by raising the current value to a given ``exponent`` a distinct number of times.

    :param initial: The starting value to use.
    :param count: The amount of times to increase the value.
    :param exponent: The power to raise the value by for each value increase.
    """

    __slots__ = ("_exponent",)

    @property
    def final(self):
        if self.count is None:
            return
        return self.initial ** self.exponent ** self.count

    @property
    def total(self):
        if self.count is None:
            return
        return sum(
            itertools.accumulate(range(1, self.count + 1), lambda s, _: s ** self.exponent, initial=self.initial)
        )

    @property
    def total_remaining(self):
        if self.count is None:
            return
        return sum(
            itertools.accumulate(range(self.count_remaining), lambda s, _: s ** self.exponent, initial=float(self))
        ) - float(self)

    @property
    def exponent(self) -> Number:
        """The power value to apply to the timer value in seconds."""
        return self._exponent

    def __init__(self, initial: Number = 1, count: int = None, exponent: Number = 2):
        super().__init__(initial=initial, count=count)
        self._exponent = exponent

    def increase(self) -> bool:
        if not self.can_increase:
            return False

        self._value **= self.exponent
        self._counter += 1
        return True


###########################################################################
## Ceiling timers
###########################################################################
class CeilingTimer(Timer, metaclass=ABCMeta):
    """
    Abstract implementation of a :py:class:`Timer` which will increment until a maximum value is reached.

    :param initial: The starting value to use.
    :param final: The value at which to stop increasing.
    """

    __slots__ = ("_final",)

    @property
    def final(self):
        return self._final

    @property
    def total(self):
        if self.final is None:
            return
        return sum(self._all_values_iter(self.initial))

    @property
    def total_remaining(self):
        if self.final is None:
            return
        return sum(self._all_values_iter(float(self))) - float(self)

    @property
    def count(self):
        if self.final is None:
            return
        return len(list(self._all_values_iter(self.initial))) - 1

    @property
    def can_increase(self) -> bool:
        return self.final is None or isinstance(self.final, Number) and self < self.final

    def __init__(self, initial: Number = 1, final: Number = None):
        super().__init__(initial=initial)

        if final is not None and final < initial:
            final = initial

        self._final = final

    def _all_values_iter(self, value: Number) -> Generator[Number, None, None]:
        """Returns an iterator for all values remaining from the given ``value`` including the given ``value``."""
        raise NotImplementedError


class StepCeilingTimer(CeilingTimer):
    """
    Increases timer value by a given ``step`` amount until a maximum value is reached.

    :param initial: The starting value to use.
    :param final: The value at which to stop increasing.
    :param step: The amount to increase the value by for each value increase.
    """

    __slots__ = ("_step",)

    @property
    def step(self) -> Number:
        """The amount to increase the timer value by in seconds."""
        return self._step

    def __init__(self, initial: Number = 1, final: Number = None, step: Number = 1):
        super().__init__(initial=initial, final=final)
        self._step = step

    def _all_values_iter(self, value: Number) -> Generator[Number, None, None]:
        if self.final is None:
            return

        yield value

        while value < self.final:
            value = min(self.final, value + self.step)
            yield value

    def increase(self) -> bool:
        if not self.can_increase:
            return False

        if self.final is not None:
            self._value = min(self.final, self._value + self.step)
        else:
            self._value += self.step

        self._counter += 1
        return True


class GeometricCeilingTimer(CeilingTimer):
    """
    Increases timer value by multiplying the current value by a given ``factor`` until a maximum value is reached.

    :param initial: The starting value to use.
    :param final: The value at which to stop increasing.
    :param factor: The amount to multiply the current value by for each value increase.
    """

    __slots__ = ("_factor",)

    @property
    def factor(self) -> Number:
        """The amount to multiply the timer value by in seconds."""
        return self._factor

    def __init__(self, initial: Number = 1, final: Number = None, factor: Number = 2):
        super().__init__(initial=initial, final=final)
        self._factor = factor

    def _all_values_iter(self, value: Number) -> Generator[Number, None, None]:
        if self.final is None:
            return

        yield value

        while value < self.final:
            value = min(self.final, value * self.factor)
            yield value

    def increase(self) -> bool:
        if not self.can_increase:
            return False

        if self.final is not None:
            self._value = min(self.final, self._value * self.factor)
        else:
            self._value *= self.factor

        self._counter += 1
        return True


class PowerCeilingTimer(CeilingTimer):
    """
    Increases timer value by raising the current value to a given ``exponent`` until a maximum value is reached.

    :param initial: The starting value to use.
    :param final: The value at which to stop increasing.
    :param exponent: The power to raise the value by for each value increase.
    """

    __slots__ = ("_exponent",)

    @property
    def exponent(self) -> Number:
        """The power value to apply to the timer value in seconds."""
        return self._exponent

    def __init__(self, initial: Number = 1, final: Number = None, exponent: Number = 2):
        super().__init__(initial=initial, final=final)
        self._exponent = exponent

    def _all_values_iter(self, value: Number) -> Generator[Number, None, None]:
        if self.final is None:
            return

        yield value

        while value < self.final:
            value = min(self.final, value ** self.exponent)
            yield value

    def increase(self) -> bool:
        if not self.can_increase:
            return False

        if self.final is not None:
            self._value = min(self.final, self._value ** self.exponent)
        else:
            self._value **= self.exponent

        self._counter += 1
        return True
