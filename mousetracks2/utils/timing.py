import time
from itertools import count
from typing import Iterator


def ticks(ups: int) -> Iterator[int]:
    """Count up at a constant speed.

    If any delay occurs, it will account for this and will continue to
    count at a constant rate, resuming from the previous tick.
    For example, if a PC gets put to sleep, then waking it up should
    resume from the tick it was put to sleep at.
    """
    start = time.time()
    for tick in count():
        yield tick

        # Calculate the expected time for the next tick
        expected = start + (tick + 1) / ups
        remaining = expected - time.time()

        # Adjust the start time to account for missed time
        if remaining < 0:
            missed_ticks = -int(remaining * ups)
            start += missed_ticks / ups
            continue

        time.sleep(remaining)
