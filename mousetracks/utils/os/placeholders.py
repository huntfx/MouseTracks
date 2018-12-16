"""This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""
#Backup functions for all the OS specific ones
#These will be loaded if an OS doesn't contain its own version, as to not crash the program

from __future__ import absolute_import

import os
import psutil
import sys

from ..compatibility import Message


def read_env_var(text):
    """Detect if text is an environment variable and read it.
    Returns:
        Value/None if successful or not.
    """
    return None
    
    
def get_running_processes():
    """Return a dictionary of running processes, with their ID as the value.
    The ID is used to determine which process was most recently loaded.
    
    This fallback function is sorted by the PID,
    which is incorrect in terms of load order.
    """
    return {i.name(): i.pid for i in psutil.process_iter()}

    
def hide_file(file_name):
    """Set a file as hidden."""
    return None

    
def show_file(file_name):
    """Unhide a file."""
    return None
    
    
def get_resolution():
    """Get the resolution of the main monitor.
    Returns:
        (x, y) resolution as a tuple.
    """
    return (1920, 1080)
    
    
def get_monitor_locations():
    """Return a list of [x[0], y[0], x[1], y[1]] coordinates for each monitor."""
    return []
    
    
def get_cursor_pos():
    """Read the cursor position on screen.
    Returns:
        (x, y) coordinates as a tuple.
        None if it can't be detected.
    """
    return None
    
    
def get_mouse_click():
    """Check if one of the three main mouse buttons is being clicked.
    Returns:
        list of True/False if any clicks have been detected or not.
    """
    return (False, False, False)

    
def get_key_press(key):
    """Check if a key is being pressed.
    Needs changing for something that detects keypresses in applications.
    Returns:
        True/False if the selected key has been pressed or not.
    """
    return False
    
    
def get_documents_path():
    """Return the path to documents."""
    return os.path.expanduser('~')

    
def get_double_click_time():
    """Get double click time in ms."""
    return 500
    
    
class WindowHandle(object):
    def __init__(self):
        self.pid = 0
    
    @property
    def rect(self):
        """Return the edge coordinates of the focused window."""
        return (0, 0, 0, 0)
        
    @property
    def name(self):
        return 'Application'
    
    #Tray icon commands (not currently in use outside of Windows)
    @property
    def minimised(self):
        return False
    
    def bring_to_front(self):
        pass
        
    def minimise(self):
        pass
        
    def hide(self):
        self.minimise()
        pass
        
        
def set_priority(level, pid=None):
    """Set the priority/nice of the application."""
    process = psutil.Process(pid)
    try:
        level = level.lower().replace(' ', '')
        
        if level == 'realtime':
            process.nice(-20)
        elif level == 'high':
            process.nice(-13)
        elif level == 'abovenormal':
            process.nice(-7)
        elif level == 'normal':
            process.nice(0)
        elif level == 'belownormal':
            process.nice(7)
        if level == 'low':
            process.nice(13)
            
    except AttributeError:
        process.nice(int(level))


def launch_console(params, visible=True, process=sys.executable):
    """Launch a new instance of Python."""
    Message('Launching a new console is not yet supported.')


def is_elevated():
    """Detect if application is currently elevated."""
    return False


tray = None