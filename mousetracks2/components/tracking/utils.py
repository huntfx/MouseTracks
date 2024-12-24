import time
from itertools import count


def ticks(ups):
    """Count up at a constant speed."""
    start = time.time()
    for tick in count():
        yield tick
        expected = start + tick / ups
        time.sleep(max(0, expected - time.time()))
