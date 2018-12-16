"""This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""
#Easy to use wrappers for sockets

from __future__ import absolute_import

import psutil
import socket
import struct
from select import select

from .compatibility import pickle


def send_msg(sock, msg):
    """Prefix each messge with length."""
    
    msg = pickle.dumps(msg)
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
    return pickle.loads(recvall(sock, msglen))

    
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


def get_ip(sock):
    """Get the IP address the socket is bound to."""
    return sock.getsockname()[0]


def get_port(sock):
    """Get the port the socket is bound to."""
    return sock.getsockname()[1]
    

def get_free_port():
    """Find a free port resulting from using port 0."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(('localhost', 0))
    port = sock.getsockname()[1]
    sock.close()
    return port
    
    
def force_close_port(port, process_name=None):
    """Terminate a process that is bound to a port.
    
    The process name can be set (eg. python), which will
    ignore any other process that doesn't start with it.
    """
    for proc in psutil.process_iter():
        for conn in proc.connections():
            if conn.laddr[1] == port:
                #Don't close if it belongs to SYSTEM
                #On windows using .username() results in AccessDenied
                #TODO: Needs testing on other operating systems
                try:
                    proc.username()
                except psutil.AccessDenied:
                    pass
                else:
                    if process_name is None or proc.name().startswith(process_name):
                        try:
                            proc.kill()
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass