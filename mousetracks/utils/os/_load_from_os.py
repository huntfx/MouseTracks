"""This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""
#Load in the operating system specific functions
#If any do not exit, a placeholder will be used instead

from __future__ import absolute_import

import platform

from . import placeholders
from ..compatibility import callable

#Load in modules from operating system
OPERATING_SYSTEM = platform.system()
if OPERATING_SYSTEM == 'Windows':
    from .windows import *
    OS_DEBUG = False
elif OPERATING_SYSTEM == 'Linux':
    from .linux import *
    OS_DEBUG = True
elif OPERATING_SYSTEM == 'Darwin':
    from .mac import *
    OS_DEBUG = True
else:
    raise ImportError('unknown operating system: "{}"'.format(OPERATING_SYSTEM))

try:
    tray_menu
except NameError:
    tray_menu = None
    
#Import placeholders if the function doesn't exist in the namespace
def _add_placeholders(variables, functions_only=False):
    """Use placeholder functions if the counterpart doesn't exist."""
    count = 0
    for f_name in dir(placeholders):
        try: 
            variables[f_name]
        except KeyError:
            f = getattr(placeholders, f_name, None)
            if not functions_only or callable(f):
                variables[f_name] = f
                count += 1
    return count
    
PLACEHOLDER_COUNT = _add_placeholders(locals())

#Check the functions exist
try:
    get_cursor_pos
    get_mouse_click
    get_key_press
    hide_file
    get_running_processes
    get_documents_path
    
    #Detect if multiple monitors can be used
    try:
        monitor_info = get_monitor_locations
        if not monitor_info():
            raise NameError
        MULTI_MONITOR = True
    except NameError:
        monitor_info = get_resolution
        MULTI_MONITOR = False
    
    #Detect if code exists to detect window focus
    try:
        WindowHandle
        FOCUS_DETECTION = True
    except NameError:
        WindowHandle = None
        FOCUS_DETECTION = False
        
except NameError:
    raise ImportError('failed to import required modules for the current operating system')