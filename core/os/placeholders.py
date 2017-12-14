"""
This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""

from __future__ import absolute_import

import os
import psutil


def elevate():
    """Run the script as an administrator.
    Fixes issues with tracking keypresses of elevated programs.
    """
    pass


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

    
def hide_file():
    """Set a file as hidden."""
    return None
    
    
def get_resolution():
    """Get the resolution of the main monitor.
    Returns:
        (x, y) resolution as a tuple.
    """
    raise NotImplementedError('not able to read the resolution')
    
    
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
    
    
class WindowFocusData(object):
    def __init__(self):
        pass
        
    def get_pid(self):
        """Return the process ID of the focused window."""
        return 0
        
    def get_rect(self):
        """Return the edge coordinates of the focused window."""
        return (0, 0, 0, 0)