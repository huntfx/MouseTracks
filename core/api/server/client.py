"""
This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""

from __future__ import absolute_import

import socket

from core.compatibility import Message, input
from core.cryptography import Crypt, DecryptionError
from core.sockets import *


def server_connect(port=None, secret=None):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    #Ask for inputs if none provided
    if port is None:
        while True:
            try:
                port = int(input('Type a port to connect to: '))
            except (TypeError, ValueError):
                pass
            else:
                break
    if secret is None:
        secret = input('Type the password to decode the messages: ')
           
    #Connect and set up decryption
    sock.connect(('localhost', port))
    crypt = Crypt(secret)
    
    #Loop through each message received
    try:
        while True:
            received_message = recv_msg(sock)
            
            #End if server has shut down
            if received_message is None:
                Message('Server appears to have stopped.')
                break
                
            #Decrypt message
            try:
                decoded_message = crypt.decrypt(received_message)
            except DecryptionError:
                Message('Incorrect password provided.')
                break
            print(decoded_message)
        sock.close()
        
    except KeyboardInterrupt:
        sock.close()