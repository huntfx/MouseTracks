"""This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""

from __future__ import absolute_import

from .server import calculate_api_timeout, server_thread as server
from .client import server_connect as client