from __future__ import absolute_import

from ..track import RefreshRateLimiter
from ..utils.compatibility import Message
from ..utils.os import get_key_press


while True:
    with RefreshRateLimiter(10):
        keys = []
        for i in range(256):
            if get_key_press(i):
                keys.append(i)
        if keys:
            Message(keys)