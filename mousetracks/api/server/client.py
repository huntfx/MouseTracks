"""This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""
#Handle client connections to a socket server

from __future__ import absolute_import

import socket

from ..constants import *
from ...cryptography import Crypt, DecryptionError
from ...config.language import LANGUAGE
from ...utils.compatibility import Message, input
from ...utils.sockets import *


def server_connect(port=None, secret=None):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    #Ask for inputs if none provided
    if port is None:
        while True:
            try:
                port = int(input(LANGUAGE.strings['Input']['PortConnect'] + ' '))
            except (TypeError, ValueError):
                pass
            else:
                break
    if secret is None:
        secret = input(LANGUAGE.strings['Input']['PortPassword'] + ' ')
           
    #Connect and set up decryption
    sock.connect(('localhost', port))
    crypt = Crypt(secret)
    
    #Loop through each message received
    try:
        while True:
            received_message = recv_msg(sock)
            
            #End if server has shut down
            if received_message == MESSAGE_QUIT:
                break
                
            elif received_message is None:
                Message(LANGUAGE.strings['Server']['MessageServerNotRunning'])
                break
            
            #Decrypt message
            else:
                try:
                    decoded_message = crypt.decrypt(received_message)
                except DecryptionError:
                    Message(LANGUAGE.strings['Server']['MessageServerIncorrectPassword'])
                    break
                except TypeError:
                    Message(LANGUAGE.strings['Server']['MessageServerDecryptError'])
                else:
                    print(decoded_message)
        sock.close()
        
    except KeyboardInterrupt:
        sock.close()