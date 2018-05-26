from __future__ import absolute_import

from core.compatibility import Message
from core.os import WindowFocus
from core.track import RefreshRateLimiter


old_app_name = None
while True:
    with RefreshRateLimiter(60):
        app_name = str(WindowFocus())
        if app_name != old_app_name:
            Message(app_name)
            old_app_name = app_name