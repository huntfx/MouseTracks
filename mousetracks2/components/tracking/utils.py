import time


class RefreshRateLimiter(object):
    """Limit the loop to a fixed updates per second.
    It works by detecting how long a frame should be,
    and comparing it to how long it's already taken.
    """
    def __init__(self, ticks):
        self.time = time.time()
        self.frame_time = 1 / ticks

    def __enter__(self):
        return self

    def __exit__(self, *args):
        time_difference = time.time() - self.time
        time.sleep(max(0, self.frame_time - time_difference))
        return False
