"""This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""
#Windows functions that don't require any special imports

from __future__ import absolute_import

import os
import psutil

from ...compatibility import PYTHON_VERSION, Message


try:
    from .pywin32 import *
except ImportError as e:
    Message('PyWin32 import failed (reason: {}). Falling back to ctypes.'.format(e))
    from .ctypes import *


def read_env_var(text):
    """Detect if text is an environment variable and read it.
    Returns:
        Value/None if successful or not.
    """
    if not text:
        return None
    if text[0] == text[-1] == '%':
        return os.getenv(text[1:-1])
    return None


def get_running_processes():
    """Return a dictionary of running processes, with their ID as the value.
    The ID is used to determine which process was most recently loaded.
    """
    task_list = os.popen("tasklist /NH /FO CSV").read().splitlines()
    
    running_processes = {}
    for i, task_raw in enumerate(task_list):
        image = task_raw.split(',', 1)[0][1:-1]
        if '.' in image:
            running_processes[image] = i
    return running_processes
    

def set_priority(level, pid=None):
    """Set the priority/nice of the application.
    
    Numbers may be used (in the style of Linux from -20 (high) to 19 (low),
    or as text, such as 'belownormal' or 'realtime'.
    """
    process = psutil.Process(pid)
    try:
        level = level.lower().replace(' ', '')
        
        if level == 'realtime':
            process.nice(psutil.REALTIME_PRIORITY_CLASS)
        elif level == 'high':
            process.nice(psutil.HIGH_PRIORITY_CLASS)
        elif level == 'abovenormal':
            process.nice(psutil.ABOVE_NORMAL_PRIORITY_CLASS)
        elif level == 'normal':
            process.nice(psutil.NORMAL_PRIORITY_CLASS)
        elif level == 'belownormal':
            process.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
        if level == 'low':
            process.nice(psutil.IDLE_PRIORITY_CLASS)
            
    except AttributeError:
        if level < -13:
            process.nice(psutil.REALTIME_PRIORITY_CLASS)
        elif -13 <= level < -7:
            process.nice(psutil.HIGH_PRIORITY_CLASS)
        elif -7 <= level < 0:
            process.nice(psutil.ABOVE_NORMAL_PRIORITY_CLASS)
        elif 0 <= level < 7:
            process.nice(psutil.NORMAL_PRIORITY_CLASS)
        elif 7 <= level < 12:
            process.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
        elif 13 <= level:
            process.nice(psutil.IDLE_PRIORITY_CLASS)