from aiorequestful.timer import Timer

timer = Timer()

timer.increase()  # increase the value
timer.wait()  # wait for the number of seconds specified by the timer's current value synchronously


async def wait() -> None:
    await timer  # as above, but wait asynchronously

value_int = int(timer)  # get the current value as an int
value_float = float(timer)  # get the current value as a float

timer.reset()  # reset the timer back to its initial settings
