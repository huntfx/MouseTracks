from __future__ import absolute_import

from ..track import RefreshRateLimiter
from ..utils.compatibility import Message
from ..utils.os import WindowFocus


old_app_name = None
while True:
    with RefreshRateLimiter(60):
        app_name = str(WindowFocus())
        if app_name != old_app_name:
            Message(app_name)
            old_app_name = app_name