from abc import ABC, ABCMeta, abstractmethod
from copy import copy, deepcopy

import pytest

from aiorequestful.request.timer import Timer
from aiorequestful.request.timer import CountTimer, StepCountTimer, GeometricCountTimer, PowerCountTimer
from aiorequestful.request.timer import CeilingTimer, StepCeilingTimer, GeometricCeilingTimer, PowerCeilingTimer


class TimerTester(ABC):

    @abstractmethod
    def timer_initial(self) -> Timer:
        raise NotImplementedError

    @pytest.fixture
    def timer_final(self, timer_initial: CountTimer) -> CountTimer:
        timer_initial = deepcopy(timer_initial)

        while timer_initial.can_increase:
            timer_initial.increase()
        return timer_initial

    @abstractmethod
    def timer_infinite(self, timer_initial: Timer) -> Timer:
        raise NotImplementedError

    @staticmethod
    def test_increased(timer_initial: Timer):
        assert timer_initial.can_increase

        initial_value = timer_initial.value
        initial_counter = timer_initial.counter

        assert timer_initial.increase()
        assert timer_initial.value > initial_value
        assert timer_initial.counter == initial_counter + 1

    @staticmethod
    def test_not_increased(timer_final: Timer):
        assert not timer_final.can_increase

        initial_value = timer_final.value
        assert not timer_final.increase()
        assert timer_final.value == initial_value

    @staticmethod
    def test_basic_properties(timer_initial: Timer, timer_final: Timer, timer_infinite: Timer):
        assert timer_initial.value == timer_initial.initial
        assert timer_initial.counter == 0
        assert timer_initial.count_remaining == timer_initial.count
        assert timer_initial.total_remaining == timer_initial.total - timer_initial.value

        assert round(timer_final.value, 2) == round(timer_final.final, 2)
        assert timer_final.count == timer_final.counter
        assert timer_final.count_remaining == 0
        assert timer_final.total_remaining == 0

        assert timer_infinite.final is None
        assert timer_infinite.total is None
        assert timer_infinite.count is None
        assert timer_infinite.count_remaining is None
        assert timer_infinite.total_remaining is None

    @staticmethod
    def test_can_increase(timer_initial: Timer, timer_final: Timer, timer_infinite: Timer):
        assert timer_initial.can_increase
        assert not timer_final.can_increase
        assert timer_infinite.can_increase

    @staticmethod
    def test_copy(timer_final: Timer):
        timer_copy = copy(timer_final)
        assert timer_copy.value == timer_final.value
        assert timer_copy.counter == timer_final.counter

        timer_deepcopy = deepcopy(timer_final)
        assert timer_deepcopy.value < timer_final.value
        assert timer_deepcopy.value == timer_final.initial
        assert timer_deepcopy.counter == 0


###########################################################################
## Count timers
###########################################################################
class CountTimerTester(TimerTester, metaclass=ABCMeta):

    @abstractmethod
    def timer_initial(self) -> CountTimer:
        raise NotImplementedError

    @pytest.fixture
    def timer_infinite(self, timer_initial: CountTimer) -> CountTimer:
        timer_initial = deepcopy(timer_initial)
        timer_initial._count = None
        return timer_initial


class TestStepCountTimer(CountTimerTester):

    @pytest.fixture
    def timer_initial(self) -> StepCountTimer:
        return StepCountTimer(initial=0.1, count=5, step=0.1)

    @staticmethod
    def test_properties():
        timer = StepCountTimer(initial=2, count=5, step=3)
        assert timer.final == 17
        assert timer.total == sum([2, 5, 8, 11, 14, 17])

        timer.increase()
        timer.increase()

        assert timer.value == 8
        assert timer.counter == 2
        assert timer.count_remaining == 3
        assert timer.total_remaining == sum([11, 14, 17])


class TestGeometricCountTimer(CountTimerTester):

    @pytest.fixture
    def timer_initial(self) -> GeometricCountTimer:
        return GeometricCountTimer(initial=0.1, count=5, factor=2)

    @staticmethod
    def test_properties():
        timer = GeometricCountTimer(initial=1, count=6, factor=2)
        assert timer.final == 64
        assert timer.total == sum([1, 2, 4, 8, 16, 32, 64])

        timer.increase()
        timer.increase()

        assert timer.value == 4
        assert timer.counter == 2
        assert timer.count_remaining == 4
        assert timer.total_remaining == sum([8, 16, 32, 64])


class TestPowerCountTimer(CountTimerTester):

    @pytest.fixture
    def timer_initial(self) -> PowerCountTimer:
        return PowerCountTimer(initial=1.1, count=5, exponent=2)

    @staticmethod
    def test_properties():
        timer = PowerCountTimer(initial=2, count=3, exponent=2)
        assert timer.final == 256
        assert timer.total == sum([2, 4, 16, 256])

        timer.increase()
        timer.increase()

        assert timer.value == 16
        assert timer.counter == 2
        assert timer.count_remaining == 1
        assert timer.total_remaining == 256


###########################################################################
## Ceiling timers
###########################################################################
class CeilingTimerTester(TimerTester, metaclass=ABCMeta):

    @abstractmethod
    def timer_initial(self) -> CeilingTimer:
        raise NotImplementedError

    @pytest.fixture
    def timer_infinite(self, timer_initial: CeilingTimer) -> CeilingTimer:
        timer_initial = deepcopy(timer_initial)
        timer_initial._final = None
        return timer_initial


class TestStepCeilingTimer(CeilingTimerTester):

    @pytest.fixture
    def timer_initial(self) -> StepCeilingTimer:
        return StepCeilingTimer(initial=0.1, final=0.5, step=0.1)

    @staticmethod
    def test_properties():
        timer = StepCeilingTimer(initial=1, final=9.5, step=2)
        assert timer.count == 5
        assert timer.total == sum([1, 3, 5, 7, 9, 9.5])

        timer.increase()
        timer.increase()

        assert timer.value == 5
        assert timer.counter == 2
        assert timer.count_remaining == 3
        assert timer.total_remaining == sum([7, 9, 9.5])


class TestGeometricCeilingTimer(CeilingTimerTester):

    @pytest.fixture
    def timer_initial(self) -> GeometricCeilingTimer:
        return GeometricCeilingTimer(initial=0.1, final=0.5, factor=2)

    @staticmethod
    def test_properties():
        timer = GeometricCeilingTimer(initial=1, final=50, factor=2)
        assert timer.count == 6
        assert timer.total == sum([1, 2, 4, 8, 16, 32, 50])

        timer.increase()
        timer.increase()

        assert timer.value == 4
        assert timer.counter == 2
        assert timer.count_remaining == 4
        assert timer.total_remaining == sum([8, 16, 32, 50])


class TestPowerCeilingTimer(CeilingTimerTester):

    @pytest.fixture
    def timer_initial(self) -> PowerCeilingTimer:
        return PowerCeilingTimer(initial=1.1, final=5, exponent=1.3)

    @staticmethod
    def test_properties():
        timer = PowerCeilingTimer(initial=2, final=50, exponent=2)
        assert timer.count == 3
        assert timer.total == sum([2, 4, 16, 50])

        timer.increase()
        timer.increase()

        assert timer.value == 16
        assert timer.counter == 2
        assert timer.count_remaining == 1
        assert timer.total_remaining == 50
