"""This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""
#Import each of the API classes and turn them into easy to use functions

from __future__ import absolute_import

from multiprocessing import Pipe
from threading import Thread

from .constants import *
from .server import server, client, calculate_api_timeout
from ..config.settings import CONFIG
from ..config.language import LANGUAGE
from ..notify import NOTIFY
from ..utils.sockets import *
from ..utils.internet import send_request
try:
    from .web import app
except ImportError as e:
    CONFIG['API']['WebServer'] = False
    CONFIG['API']['WebServer'].lock = True
    NOTIFY(LANGUAGE.strings['Misc']['ImportFailed'], MODULE='web server', REASON=e)
    app = None


def local_message_server(q_main, port=0, close_port=False, server_secret=None, q_feedback=None):
    """Start a threaded server to send queue information to connected clients."""
    kwargs = {'q_main': q_main, 'port': port, 'close_port': close_port, 'server_secret': server_secret, 'q_feedback': q_feedback}
    server_thread = Thread(target=server, kwargs=(kwargs))
    server_thread.daemon = True
    server_thread.start()
    return server_thread

    
def local_message_connect(port=None, secret=None):
    client(port=port, secret=secret)
    
    
def local_web_server(app, port=0, q_feedback=None):
    """Start a web server."""
    NOTIFY(LANGUAGE.strings['Server']['FlaskStart'])
    web_thread = Thread(target=app.run, kwargs={'port': port})
    web_thread.daemon = True
    web_thread.start()
    NOTIFY(LANGUAGE.strings['Server']['FlaskPort'], PORT=port)
    return web_thread


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