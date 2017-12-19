"""
This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""

from __future__ import absolute_import

from threading import Thread

from core.api.constants import *
from core.api.server import server_thread
from core.api.web import app, create_pipe
from core.sockets import *


def local_message_server(q_main=None, port=0, close_port=False, q_feedback=None):
    """Start a threaded server to send queue information to connected clients."""
    kwargs = {'port': port, 'q_main': q_main, 'close_port': close_port, 'q_feedback': q_feedback}
    server = Thread(target=server_thread, kwargs=(kwargs))
    server.daemon = True
    server.start()
    
    
def local_web_server(app, port=0):
    """Start a web server."""
    server = Thread(target=app.run, kwargs={'port': port})
    server.daemon = True
    server.start()