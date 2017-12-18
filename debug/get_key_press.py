from __future__ import absolute_import

from core.compatibility import Message
from core.os import get_key_press
from core.track import RefreshRateLimiter


while True:
    with RefreshRateLimiter(10):
        keys = []
        for i in range(256):
            if get_key_press(i):
                keys.append(i)
        if keys:
            Message(keys)