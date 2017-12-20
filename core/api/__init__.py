"""
This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""

from __future__ import absolute_import

from threading import Thread

from core.api.constants import *
from core.api.server import server_thread
from core.api.web import app, create_pipe
from core.notify import *
from core.sockets import *


def local_message_server(q_main, port=0, close_port=False, q_feedback=None):
    """Start a threaded server to send queue information to connected clients."""
    kwargs = {'q_main': q_main, 'port': port, 'close_port': close_port, 'q_feedback': q_feedback}
    server = Thread(target=server_thread, kwargs=(kwargs))
    server.daemon = True
    server.start()
    
    
def local_web_server(app, port=0, q_feedback=None):
    """Start a web server."""
    NOTIFY(SERVER_WEB_START)
    server = Thread(target=app.run, kwargs={'port': port})
    server.daemon = True
    server.start()
    NOTIFY(SERVER_WEB_PORT, port)