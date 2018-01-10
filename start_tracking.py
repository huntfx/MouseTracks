"""
This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""

from __future__ import absolute_import

from multiprocessing import freeze_support

from core.config import CONFIG
from core.track import start_tracking
from core.os import elevate, tray


if __name__ == '__main__':
    
    freeze_support()
    
    if CONFIG['Advanced']['RunAsAdministrator']:
        elevate()
    
    #Run normally
    if tray is None or not CONFIG['API']['RunWeb']:
        start_tracking()
    
    #Create tray icon
    else:
        from threading import Thread
        
        from core.api import local_address, shutdown_server
        from core.compatibility import Message
        from core.internet import get_url_json, send_request
        from core.files import Lock
        from core.notify import *
        from core.sockets import get_free_port
        
        
        def _end_thread(thread, web_port):
            """Close the tracking thread."""
            if web_port is not None:
                shutdown_server(web_port)
            thread.join()
        
        def _start_tracking(cls, web_port=None, _thread=None):
            """Start new tracking thread after closing old one."""
            #End old thread
            if _thread:
                _end_thread(_thread, web_port)
                NOTIFY(TRACKING_RESTART)
                web_port = None
            
            #Start thread
            web_port = get_free_port() if web_port is None else web_port
            thread = Thread(target=start_tracking, kwargs={'web_port': web_port, 'console': False, 'lock': False})
            thread.start()
        
            #Set new port
            if cls is not None and _thread:
                cls.set_menu_item('track', name='Pause Tracking', kwargs={'web_port': web_port})
                cls.set_menu_item('exit', kwargs={'web_port': web_port, 'thread': thread})
                if _thread:
                    cls.set_menu_item('restart', kwargs={'_thread': thread})
            return thread

        def toggle_tracking(cls, web_port):
            """Pause or resume tracking.
            Add a timeout for if the script crashes.
            """
            status_url = '{}/status'.format(local_address(web_port))
            status = get_url_json(status_url, timeout=1)
            
            if status == 'running':
                send_request('{}/stop'.format(status_url), timeout=1, output=True)
            elif status == 'stopped':
                send_request('{}/start'.format(status_url), timeout=1, output=True)
            
        def quit(cls, thread, web_port):
            """End the script and close the window."""
            _end_thread(thread, web_port)
            tray.quit(cls)
        
        def on_menu_open(cls):
            """Run this just before the menu opens."""
            status_url = '{}/status'.format(local_address(web_port))
            status = get_url_json(status_url, timeout=0.25)
            
            if status == 'running':
                cls.set_menu_item('track', name='Pause Tracking', hidden=False)
            elif status == 'stopped':
                cls.set_menu_item('track', name='Start Tracking', hidden=False)
            cls._refresh_menu()
                
        def on_menu_close(cls):
            """Run this after the menu has closed."""
            cls.set_menu_item('track', hidden=True)
            
        
        web_port = get_free_port()
        thread = _start_tracking(None, web_port)
        menu_options = (
            {'id': 'track', 'name': 'wat', 'action': toggle_tracking, 'hidden': True, 'kwargs': {'web_port': web_port}},
            {'id': 'restart', 'name': 'Restart', 'action': _start_tracking, 'kwargs': {'web_port': web_port, '_thread': thread}},
            {'id': 'exit', 'name': 'Quit', 'action': quit, 'kwargs': {'web_port': web_port, 'thread': thread}},
        )
        
        with Lock() as locking:
            if locking is not None:
                t = tray.Tray(menu_options, menu_open=on_menu_open, menu_close=on_menu_close)
                t.listen()
            else:
                Message(NOTIFY(PROCESS_NOT_UNIQUE).get_output())