"""This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""
#Create a socket server to accept multiple client connections
#Uses a triple threaded approach to receive data and send it to each client,
#while accepting any new connections

from __future__ import absolute_import

import random
import socket
import uuid
from multiprocessing import Queue
from threading import Thread, currentThread

from ..constants import *
from ...config.settings import CONFIG
from ...constants import UPDATES_PER_SECOND
from ...cryptography import Crypt
from ...config.language import LANGUAGE
from ...notify import NOTIFY
from ...utils.compatibility import queue, range
from ...utils.sockets import *


def _generate_code(length):
    """Generate a random code."""
    return str(uuid.uuid4())


def calculate_api_timeout():
    """Calculate the correct timeout so it doesn't crash if using a higher polling rate."""
    return CONFIG['Advanced']['APIPollingRate'] / UPDATES_PER_SECOND + 1
    

def client_thread(client_id, sock, q_recv, q_send):
    """Send data to the connected clients."""
    #Connect to client and send feedback
    conn, addr = sock.accept()
    q_send.put(addr)
    
    #Remove items from queue sent before connection
    try:
        while not q_recv.empty():
            if q_recv.get() == MESSAGE_IGNORE:
                break
    except IOError:
        conn.close()
        return
    
    #Send each item to the client
    t = currentThread()
    while getattr(t, 'running', True):
        try:
            message = q_recv.get()
        except (IOError, EOFError):
            return
        try:
            send_msg(conn, message)
        except (socket.error, KeyboardInterrupt):
            conn.close()
            return
            
            
def middleman_thread(encrypt_code, q_main, q_list, exit_on_disconnect=True):
    """Handle the incoming queue and duplicate for all clients."""
    crypt = Crypt(encrypt_code)
    
    #This will cut off all messages from before the previous connection
    try:
        q_list[-1].put(MESSAGE_IGNORE)
    except (IOError, EOFError):
        return
    
    #Loop through and wait for input messages
    t = currentThread()
    while getattr(t, 'running', True):
        try:
            message = q_main.get(timeout=calculate_api_timeout())
        except queue.Empty:
            pass
        except (IOError, EOFError):
            return
        else:
            if message == MESSAGE_QUIT:
                queues = q_list[:-1]
            elif message == MESSAGE_IGNORE:
                queues = q_list[-1]
            else:
                message = crypt.encrypt(message)
                queues = q_list
                
            #Send to client threads
            for q in queues:
                try:
                    q.put(message)
                except AssertionError:
                    if exit_on_disconnect:
                        return
                except (IOError, EOFError):
                    return
                        

def server_thread(q_main, host='localhost', port=0, server_secret=None, close_port=False, q_feedback=None):
    """Run a server to send messages to all the connected clients."""
    
    #Create server socket
    NOTIFY(LANGUAGE.strings['Server']['MessageStart'])
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind((host, port))
    except socket.error as e:
        if e.errno == 10048:
            NOTIFY(LANGUAGE.strings['Server']['PortTaken'], PORT=port)
            if close_port:
                NOTIFY(LANGUAGE.strings['Server']['PortClose'], PORT=port)
                force_close_port(port)
            else:
                NOTIFY(LANGUAGE.strings['Server']['PortRandom'])
                port = 0
            sock.bind((host, port))
        else:
            raise socket.error('unable to start server')
    sock.listen(5)
    
    NOTIFY(LANGUAGE.strings['Server']['MessagePort'], PORT=sock.getsockname()[1])
    
    #Generate a code needed for connections
    if server_secret is None:
        server_secret = _generate_code(15)
    NOTIFY(LANGUAGE.strings['Server']['MessageSecretSet'], SECRET=server_secret)
    
    q_conn = Queue()
    threads = []
    queues = []
    client_id = 1
    try:
        t = currentThread()
        while getattr(t, 'running', True):
            #Start new client thread
            queues.append(Queue())
            threads.append(Thread(target=client_thread, args=(client_id, sock, queues[-1], q_conn)))
            threads[-1].daemon = True
            threads[-1].start()
            
            #Restart the message intercept thread
            try:
                middleman.running = False
                middleman.join()
            except NameError:
                pass
            middleman = Thread(target=middleman_thread, args=(server_secret, q_main, tuple(queues)))
            middleman.daemon = True
            middleman.start()
            
            #Check for new connection (the latest thread is idle until then)
            #Loop is needed so that KeyboardInterrupt can be intercepted
            NOTIFY(LANGUAGE.strings['Server']['MessageListen'])
            while True:
            
                #Close all client connections
                if getattr(t, 'force_close_clients', False):
                    try:
                        q_main.put(MESSAGE_QUIT)
                    except (IOError, EOFError):
                        pass
                    t.force_close_clients = False
            
                try:
                    addr = q_conn.get(timeout=calculate_api_timeout())
                    
                #No connection yet
                except queue.Empty:
                    pass
                    
                #New client connected
                else:
                    NOTIFY(LANGUAGE.strings['Server']['MessageConnection'], HOST=addr[0], PORT=addr[1])
                    client_id += 1
                    break

            #Delete closed connections
            invalid = []
            for i, thread in enumerate(threads):
                if not thread.isAlive():
                    invalid.append(i)
            for i in invalid[::-1]:
                del threads[i]
                queues[i].close()
                del queues[i]
    
    #Safely shut down threads and queues
    except KeyboardInterrupt:
        for thread in threads:
            thread.running = False
        for q in queues:
            q.close()
        middleman.running = False
        sock.close()
        
    except (IOError, EOFError):
        sock.close()