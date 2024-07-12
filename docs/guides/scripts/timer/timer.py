# PART 1

from aiorequestful.timer import StepCountTimer

timer = StepCountTimer(initial=0, count=3, step=0.2)  # value = 0
timer.increase()  # value = 0.2
timer.increase()  # value = 0.4
timer.increase()  # value = 0.6
timer.increase()  # value = 0.6 (max count of 3 reached)

print(float(timer))

# PART 2

from aiorequestful.timer import GeometricCountTimer

timer = GeometricCountTimer(initial=2, count=3, factor=2)  # value = 2
timer.increase()  # value = 4
timer.increase()  # value = 8
timer.increase()  # value = 16
timer.increase()  # value = 16 (max count of 3 reached)

print(float(timer))

# PART 3

from aiorequestful.timer import PowerCountTimer

timer = PowerCountTimer(initial=2, count=3, exponent=2)  # value = 2
timer.increase()  # value = 4
timer.increase()  # value = 16
timer.increase()  # value = 256
timer.increase()  # value = 256 (max count of 3 reached)

print(float(timer))

# PART 4

from aiorequestful.timer import StepCeilingTimer

timer = StepCeilingTimer(initial=0, final=0.5, step=0.2)  # value = 0
timer.increase()  # value = 0.2
timer.increase()  # value = 0.4
timer.increase()  # value = 0.5 (max value reached)
timer.increase()  # value = 0.5

print(float(timer))

# PART 5

from aiorequestful.timer import GeometricCeilingTimer

timer = GeometricCeilingTimer(initial=2, final=10, factor=2)  # value = 2
timer.increase()  # value = 4
timer.increase()  # value = 8
timer.increase()  # value = 10 (max value reached)
timer.increase()  # value = 10

print(float(timer))

# PART 6

from aiorequestful.timer import PowerCeilingTimer

timer = PowerCeilingTimer(initial=2, final=60, exponent=2)  # value = 2
timer.increase()  # value = 4
timer.increase()  # value = 16
timer.increase()  # value = 60 (max value reached)
timer.increase()  # value = 60

print(float(timer))
