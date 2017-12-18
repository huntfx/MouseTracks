from __future__ import absolute_import

from core.compatibility import Message
from core.os import WindowFocus
from core.track import RefreshRateLimiter


while True:
    with RefreshRateLimiter(10):
        Message(WindowFocus())