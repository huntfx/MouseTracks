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


AUTOMATIC_PORT = False

SERVER_PORT = 60154 #This port is only used if automatic is disabled


def start_message_server(q_main=None, host='localhost', port=None, close_port=False, q_feedback=None):
    """Start a threaded server to send queue information to connected clients."""
        
    port = 0 if AUTOMATIC_PORT else SERVER_PORT
    
    server = Thread(target=server_thread, args=(host, port, q_main, close_port, q_feedback))
    server.daemon = True
    server.start()
    
    
def start_web_server(app, port=0):
    """Start a web server."""
    server = Thread(target=app.run, kwargs={'port': port})
    server.daemon = True
    server.start()