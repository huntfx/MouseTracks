"""
This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""

from __future__ import absolute_import

import cPickle
import socket
import struct
from select import select


def send_msg(sock, msg):
    """Prefix each messge with length."""
    
    msg = cPickle.dumps(msg)
    msg = struct.pack('>I', len(msg)) + msg
    sock.sendall(msg)
    
    
def recv_msg(sock):
    """Receive the message."""
    
    #Read message length
    raw_msglen = recvall(sock, 4)
    if not raw_msglen:
        return None
    msglen = struct.unpack('>I', raw_msglen)[0]
    
    #Read message data
    return cPickle.loads(recvall(sock, msglen))

    
def recvall(sock, n):
    """Receive socket data and detect if the connection was closed."""
    data = ''
    while len(data) < n:
        packet = sock.recv(n - len(data))
        if not packet:
            return None
        data += packet
    return data


def msg_empty(sock):
    """Detect if socket is empty."""
    return not select([sock],[],[],0)[0]