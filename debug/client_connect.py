"""
This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""

from __future__ import absolute_import

import socket

from core.api import AUTOMATIC_PORT, SERVER_PORT
from core.compatibility import input
from core.sockets import *


sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    port = int(input('Type a port to connect to, or leave blank to use {}:'.format(SERVER_PORT)))
except (TypeError, ValueError):
    port = SERVER_PORT
sock.connect(('localhost', SERVER_PORT))

try:
    #Print every received message
    while True:
        message = recv_msg(sock)
        if message is None:
            sock.close()
            break
        print(message)
        
except KeyboardInterrupt:
    sock.close()