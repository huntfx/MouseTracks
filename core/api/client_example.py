"""
This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""

from __future__ import absolute_import

import socket

from core.api import AUTOMATIC_PORT, SERVER_PORT
from core.sockets import *


if __name__ == '__main__':
    client_process = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_process.connect(('localhost', SERVER_PORT))

    try:
        #Print every received message
        while True:
            message = recv_msg(client_process)
            if message is None and msg_empty(client_process):
                client_process.close()
                break
            print(message)
            
    except KeyboardInterrupt:
        client_process.close()