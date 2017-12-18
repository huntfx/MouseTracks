"""
This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""

from __future__ import absolute_import

from multiprocessing import Queue
from threading import Thread, currentThread
from queue import Empty
import socket

from core.sockets import *


POLLING_RATE = 0.1


def client_thread(client_id, sock, q_recv, q_send):
    """Send data to the connected clients."""
    #Connect to client and send feedback
    conn, addr = sock.accept()
    q_send.put(addr)
    
    #Remove earlier items from queue
    while not q_recv.empty():
        q_recv.get()
    
    #Send each item to the client
    thread = currentThread()
    while getattr(thread, 'running', True):
        message = q_recv.get()
        try:
            send_msg(conn, '{}: {}'.format(client_id, message))
        except (socket.error, KeyboardInterrupt):
            conn.close()
            return
            
            
def middleman_thread(q_main, q_list, exit_on_disconnect=True):
    """Handle the incoming queue and duplicate for all clients."""
    thread = currentThread()
    while getattr(thread, 'running', True):
        try:
            message = q_main.get(timeout=POLLING_RATE)
        except Empty:
            pass
        else:
            for q in q_list:
                try:
                    q.put(message)
                except AssertionError:
                    if exit_on_disconnect:
                        return
                        

def server_thread(host='localhost', port=0, q_main=None, close_port=False):
    """Run a server to send messages to all the connected clients."""

    #Setup temporary queue if none provided
    debug = False
    if q_main is None:
        q_main = Queue()
        debug = True
    
    #Create server socket
    print 'Starting server...'
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind((host, port))
    except socket.error as e:
        if e.errno == 10048:
            print 'Port {} currently in use.'.format(port)
            if close_port:
                print 'Closing process...'
                force_close_port(port)
            else:
                print 'Selecting a new one...'
                port = 0
            sock.bind((host, port))
        else:
            raise socket.error('unable to start server')
    sock.listen(5)
    
    print 'Port set to {}'.format(sock.getsockname())
    
    q_conn = Queue()
    threads = []
    queues = []
    client_id = 1
    try:
        while True:
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
            middleman = Thread(target=middleman_thread, args=(q_main, tuple(queues)))
            middleman.daemon = True
            middleman.start()
            
            #Check for new connection (the latest thread is idle until then)
            #Loop is needed so that KeyboardInterrupt can be intercepted
            if debug:
                q_main.put('Waiting for new connection...')
            while True:
                try:
                    addr = q_conn.get(timeout=POLLING_RATE)
                #No connection yet
                except Empty:
                    pass
                #New client connected
                else:
                    if debug:
                        q_main.put('{}:{} connected.'.format(*addr))
                    client_id += 1
                    break
        
    except KeyboardInterrupt:
        for thread in threads:
            thread.running = False
        for q in queues:
            q.close()
        helper.running = False
        sock.close()