from __future__ import absolute_import

from core.compatibility import _print
from core.os import WindowFocus
from core.track import RefreshRateLimiter


while True:
    with RefreshRateLimiter(10):
        _print(WindowFocus())