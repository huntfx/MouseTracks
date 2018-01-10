"""
This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""

from __future__ import absolute_import

from multiprocessing import Pipe
from threading import Thread

from core.api.constants import *
from core.api.server import server_thread
from core.config import CONFIG
from core.internet import send_request
from core.notify import *
from core.sockets import *
try:
    from core.api.web import app
except ImportError:
    CONFIG['API']['RunWeb'] = False
    CONFIG['API']['RunWeb'].lock = True
    NOTIFY(IMPORT_FAILED, 'Flask')
    app = None


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


def create_pipe(name, duplex=False):
    """Create two pipes for sending/receiving data."""
    name_recv = 'PIPE_{}_RECV'.format(name)
    name_send = 'PIPE_{}_SEND'.format(name)
    recv, send = Pipe(duplex=duplex)
    return {name_recv: recv, name_send: send}
    
    
def local_address(port):
    """Return the local IP with port."""
    return 'http://127.0.0.1:{}'.format(port)
    
    
def shutdown_server(port, timeout=1):
    """Send API request to shut down server."""
    send_request('{}/status/terminate'.format(local_address(port)), timeout=timeout, output=True)