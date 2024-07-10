import asyncio
import itertools
from abc import ABC, ABCMeta, abstractmethod
from asyncio import sleep
from collections.abc import Awaitable, Generator
from copy import deepcopy

from aiorequestful.types import Number


class Timer(ABC):
    @property
    def value(self) -> Number:
        """The current timer value in seconds."""
        return self._value

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

    def reset(self) -> None:
        """Reset the timer to its initial settings."""
        self._value = self.initial
        self._counter = 0

    @abstractmethod
    def increase(self) -> bool:
        """
        Increase the timer value.

        :return: True if timer was increased, False if not.
        """
        raise NotImplementedError

    def __await__(self) -> Awaitable:
        """Asynchronously sleep for the current time set for this timer."""
        return asyncio.sleep(self.value)

    def wait(self) -> None:
        """Sleep for the current time set for this timer."""
        sleep(self.value)

    def __deepcopy__(self, memo: dict):
        cls = self.__class__
        obj = cls.__new__(cls)

        memo[id(self)] = obj
        for k, v in self.__dict__.items():
            setattr(obj, k, deepcopy(v, memo))

        obj.reset()
        return obj


###########################################################################
## Count timers
###########################################################################
class CountTimer(Timer, metaclass=ABCMeta):

    @property
    def value(self):
        return self._value

    @property
    def initial(self):
        return self._initial

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

    @property
    def value(self):
        return self._value

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
        return sum(self.value + self.step * i for i in range(self.count_remaining + 1)) - self.value

    @property
    def step(self) -> Number:
        """The amount to increase the timer value by in seconds."""
        return self._step

    def __init__(self, initial: Number = 1, count: int = None, step: Number = 2):
        super().__init__(initial=initial, count=count)
        self._step = step

    def increase(self) -> bool:
        if not self.can_increase:
            return False

        self._value += self.step
        self._counter += 1
        return True


class GeometricCountTimer(CountTimer):

    @property
    def value(self):
        return self._value

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
            itertools.accumulate(range(self.count_remaining), lambda s, _: s * self.factor, initial=self.value)
        ) - self.value

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

    @property
    def value(self):
        return self._value

    @property
    def final(self):
        if self.count is None:
            return
        return self.initial ** self.factor ** self.count

    @property
    def total(self):
        if self.count is None:
            return
        return sum(
            itertools.accumulate(range(1, self.count + 1), lambda s, _: s ** self.factor, initial=self.initial)
        )

    @property
    def total_remaining(self):
        if self.count is None:
            return
        return sum(
            itertools.accumulate(range(self.count_remaining), lambda s, _: s ** self.factor, initial=self.value)
        ) - self.value

    @property
    def factor(self) -> Number:
        """The power value to apply to the timer value in seconds."""
        return self._factor

    def __init__(self, initial: Number = 1, count: int = None, factor: Number = 2):
        super().__init__(initial=initial, count=count)
        self._factor = factor

    def increase(self) -> bool:
        if not self.can_increase:
            return False

        self._value **= self.factor
        self._counter += 1
        return True


###########################################################################
## Ceiling timers
###########################################################################
class CeilingTimer(Timer, metaclass=ABCMeta):

    @property
    def value(self):
        return self._value

    @property
    def initial(self):
        return self._initial

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
        return sum(self._all_values_iter(self.value)) - self.value

    @property
    def count(self):
        if self.final is None:
            return
        return len(list(self._all_values_iter(self.initial))) - 1

    @property
    def can_increase(self) -> bool:
        return self.final is None or isinstance(self.final, Number) and self._value < self.final

    def __init__(self, initial: Number = 1, final: Number = None):
        super().__init__(initial=initial)

        if final is not None and final < initial:
            final = initial

        self._final = final

    def _all_values_iter(self, value: Number) -> Generator[Number, None, None]:
        """Returns an iterator for all values remaining from the given ``value`` including the given ``value``."""
        raise NotImplementedError


class StepCeilingTimer(CeilingTimer):

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

    @property
    def factor(self) -> Number:
        """The power value to apply to the timer value in seconds."""
        return self._factor

    def __init__(self, initial: Number = 1, final: Number = None, factor: Number = 2):
        super().__init__(initial=initial, final=final)
        self._factor = factor

    def _all_values_iter(self, value: Number) -> Generator[Number, None, None]:
        if self.final is None:
            return

        yield value

        while value < self.final:
            value = min(self.final, value ** self.factor)
            yield value

    def increase(self) -> bool:
        if not self.can_increase:
            return False

        if self.final is not None:
            self._value = min(self.final, self._value ** self.factor)
        else:
            self._value **= self.factor

        self._counter += 1
        return True
