"""This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""
#Basic function to show how a client connection can be done

from __future__ import absolute_import

import socket

from ..cryptography import Crypt, DecryptionError
from ..utils.compatibility import input
from ..utils.sockets import *


def server_connect(port=None):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    if port is None:
        while True:
            try:
                port = int(input('Type a port to connect to: '))
            except (TypeError, ValueError):
                pass
            else:
                break
        password = input('Type the password to decode the messages: ')
        sock.connect(('localhost', port))
        
    crypt = Crypt(password)
    try:
        #Print every received message
        while True:
            try:
                message = crypt.decrypt(recv_msg(sock))
            except DecryptionError:
                print('Incorrect password provided.')
                break
            if message is None:
                print('Server appears to have stopped.')
                break
            print(message)
        sock.close()
        
    except KeyboardInterrupt:
        sock.close()