"""
This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""

from __future__ import absolute_import, division

import platform
import psutil
import os

from core.os import placeholders


#Make sure exceptions exist as they are platform specific
#If mac is similar to linux then this can be cleaned later
try:
    WindowsError
except NameError:
    class WindowsError(OSError): pass
try:
    FileNotFoundError
except NameError:
    class FileNotFoundError(OSError): pass
try:
    FileExistsError
except NameError:
    class FileExistsError(OSError): pass


#Define any functions
def remove_file(file_name):
    try:
        os.remove(file_name)
    except (OSError, FileNotFoundError, WindowsError):
        return False
    return True


def rename_file(old_name, new_name):
    try:
        os.rename(old_name, new_name)
    except (OSError, FileNotFoundError, WindowsError):
        return False
    return True

    
def file_exists(file_name):
    return os.path.isfile(file_name)
    

def create_folder(folder_path):
    
    #Remove file from path
    folders = folder_path.replace('\\', '/').split('/')
    if not folders[-1] or '.' in folders[-1][1:]:
        folder_path = '/'.join(folders[:-1])
    
    try:
        os.makedirs(folder_path)
    except (OSError, FileExistsError, WindowsError):
        return False
    return True

    
def get_modified_time(file_name):
    try:
        return os.path.getmtime(file_name)
    except (OSError, FileNotFoundError, WindowsError):
        return None
    
    
def list_directory(folder):
    try:
        return os.listdir(folder)
    except (OSError, FileNotFoundError, WindowsError):
        return None

        
def file_exists(path):
    return os.path.exists(path)
    

def join_path(path, create=False):
    """Join a path, and create folder if needed."""
    joined = os.path.join(*path)
    if create:
        create_folder(joined)
    return joined
    
    
def open_folder(path):
    os.startfile(path)


#Set which keys to check
KEYS = {
    'THUMB1': 5,
    'THUMB2': 6,
    'BACK': 8,
    'TAB': 9,
    'CLEAR': 12,
    'RETURN': 13,
    'PAUSE': 19,
    'CAPSLOCK': 20,
    'ESC': 27,
    'SPACE': 32,
    'PGUP': 33,
    'PGDOWN': 34,
    'END': 35,
    'HOME': 36,
    'LEFT': 37,
    'UP': 38,
    'RIGHT': 39,
    'DOWN': 40,
    'INSERT': 45,
    'DELETE': 46,
    'LWIN': 91,
    'RWIN': 92,
    'MENU': 93,
    'NUM0': 96,
    'NUM1': 97,
    'NUM2': 98,
    'NUM3': 99,
    'NUM4': 100,
    'NUM5': 101,
    'NUM6': 102,
    'NUM7': 103,
    'NUM8': 104,
    'NUM9': 105,
    'MULTIPLY': 106,
    'ADD': 107,
    'SUBTRACT': 109,
    'DECIMAL': 110,
    'DIVIDE': 111,
    'F1': 112,
    'F2': 113,
    'F3': 114,
    'F4': 115,
    'F5': 116,
    'F6': 117,
    'F7': 118,
    'F8': 119,
    'F9': 120,
    'F10': 121,
    'F11': 122,
    'F12': 123,
    'F13': 124,
    'F14': 125,
    'F15': 126,
    'F16': 127,
    'F17': 128,
    'F18': 129,
    'F19': 130,
    'F20': 131,
    'F21': 132,
    'F22': 133,
    'F23': 134,
    'F24': 135,
    'NUMLOCK': 144,
    'SCROLLLOCK': 145,
    'LSHIFT': 160,
    'RSHIFT': 161,
    'LCTRL': 162,
    'RCTRL': 163,
    'LALT': 164,
    'RALT': 165,
    'COLON': 186,
    'EQUALS': 187,
    'COMMA': 188,
    'UNDERSCORE': 189,
    'PERIOD': 190,
    'FORWARDSLASH': 191,
    'AT': 192,
    'LBRACKET': 219,
    'BACKSLASH': 220,
    'RBRACKET': 221,
    'HASH': 222,
    'TILDE': 223
}
for c in list('ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890'):
    KEYS[c] = ord(c)
    

#Load in modules from operating system
OPERATING_SYSTEM = platform.system()
if OPERATING_SYSTEM == 'Windows':
    try:
        from core.os.windows import *
    except ImportError:
        raise ImportError('missing required modules for windows')
    OS_DEBUG = False
elif OPERATING_SYSTEM == 'Linux':
    try:
        from core.os.linux import *
    except ImportError:
        raise ImportError('missing required modules for linux')
    OS_DEBUG = True
elif OPERATING_SYSTEM == 'Darwin':
    try:
        from core.os.mac import *
    except ImportError:
        raise ImportError('missing required modules for mac')
    OS_DEBUG = True
else:
    raise ImportError('unknown operating system: "{}"'.format(OPERATING_SYSTEM))

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
        WindowFocusData
        FOCUS_DETECTION = True
    except NameError:
        FOCUS_DETECTION = False
        
except NameError:
    raise ImportError('failed to import required modules for the current operating system')

    
if FOCUS_DETECTION:

    def _get_memory_percent(process):
        total = process.memory_percent()
        for child in process.children():
            total += _get_memory_percent(child)
        return total
    
    
    class WindowFocus(object):
        """Get information about the currently focused window.
        
        The WindowFocusData class will be queried first, 
        and psutil will be used if the function doesn't exist.
        """
        def __init__(self):
            self.window_data = WindowFocusData()
            self._psutil = None
        
        def __str__(self):
            return 'Process {} ({}): {}'.format(self.pid(), self.exe(), self.name())
    
        def psutil(self):
            if self._psutil is None:
                self._psutil = psutil.Process(self.pid())
            return self._psutil
    
        def pid(self):
            """Get the process ID of the focused window."""
            return self.window_data.get_pid()
        
        def exe(self):
            """Get the name of the currently running process."""
            try:
                return self.window_data.get_exe()
            except AttributeError:
                try:
                    return self.psutil().name()
                except psutil.NoSuchProcess:
                    return None
        
        def rect(self):
            """Get the corner coordinates of the focused window."""
            return self.window_data.get_rect()
        
        def resolution(self):
            try:
                return self.window_data.get_resolution()
            except AttributeError:
                x0, y0, x1, y1 = self.rect()
                x_res = x1 - x0
                y_res = y1 - y0
                return (x_res, y_res)
        
        def name(self):
            try:
                return self.window_data.get_name()
            except AttributeError:
                return True
        
        #Not in use but may be useful later
        def percentage_memory_usage(self):
            try:
                return self.window_data.get_memory_percentage()
            except AttributeError:
                try:
                    return _get_memory_percent(self.psutil())
                except psutil.NoSuchProcess:
                    return 0
        
        def memory_usage(self):
            try:
                memory_size = get_memory_size()
            except NameError:
                try:
                    memory_size = psutil.virtual_memory().total
                except psutil.NoSuchProcess:
                    return 0
            return int(memory_size * self.percentage_memory_usage() / 100)
        
        def cmd_args(self):
            try:
                return self.window_data.get_cmdline()
            except AttributeError:
                try:
                    return self.psutil().cmdline()
                except psutil.NoSuchProcess:
                    return None
            
        def working_directory(self):
            try:
                return self.window_data.get_working_directory()
            except AttributeError:
                try:
                    return self.psutil().cwd()
                except psutil.NoSuchProcess:
                    return None
            
else:
    WindowFocus = None