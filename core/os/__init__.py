"""
This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""

from __future__ import absolute_import, division

import psutil
import os

from core.os import console


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
def _get_folder_path(file_path, force_file=False, force_folder=False):
    """Remove the last item from a path if it is a file.
    Returns a tuple of the folder path, and file name if set or None.
    
    As a file or folder may be in the format "/.file" or "/.folder",
    if it doesn't already exist, you may set force_file or force_folder.
    """
    #If location exists
    if os.path.exists(file_path):
        if os.path.isfile(file_path):
            folders = file_path.replace('\\', '/').split('/')
            return '/'.join(folders[:-1]), folders[-1]
        return file_path, None
    
    #If location doesn't exist
    folders = file_path.replace('\\', '/').split('/')
    if force_file or not force_folder and '.' in folders[-1]:
        return '/'.join(folders[:-1]), folders[-1]
    return file_path, None
    
    
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
    

def create_folder(folder_path, is_file=None):
    
    force_file = False if is_file is None else is_file
    force_folder = False if is_file is None else not is_file
    folder_path, file_path = _get_folder_path(folder_path, force_file=force_file, force_folder=force_folder)
    
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

    
def set_modified_time(path, time):
    try:
        os.utime(path, (time, time))
    except (OSError, FileNotFoundError, WindowsError):
        return False
    return True
    
    
def list_directory(folder, remove_extensions=False, force_extension=None):
    try:
        files = os.listdir(folder)
        if force_extension:
            files = [f for f in files if f.lower().endswith(force_extension)]
        if remove_extensions:
            files = ['.'.join(f.split('.')[:-1]) for f in files]
        return files
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
    try:
        os.startfile(path)
    except (OSError, FileNotFoundError, WindowsError):
        return False
    return True
    

#Functions to be used with commands
def load_executable(path):
    
    folder_path, file_path = _get_folder_path(path)
    
    os.chdir(folder_path)
    os.system(path)
    

def process_terminate(pid, wait=False):
    p = psutil.Process(pid)
    if wait:
        if isinstance(wait, bool):
            p.wait()
        else:
            p.wait(wait)
    else:
        p.terminate()


def process_suspend(pid):
    p = psutil.Process(pid)
    p.suspend()


def process_resume(pid):
    p = psutil.Process(pid)
    p.resume()
    
    
def mouse_press(button):
    raise NotImplementedError
    
def mouse_move(x, y):
    raise NotImplementedError
    
def key_press(key):
    raise NotImplementedError
    

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
    

from core.os._load_from_os import *

    
if FOCUS_DETECTION:

    def _get_memory_percent(process):
        total = process.memory_percent()
        for child in process.children():
            total += _get_memory_percent(child)
        return total
    
    
    class WindowFocus(object):
        """Get information about the currently focused window.
        
        The WindowHandle class will be queried first, 
        and psutil will be used if the function doesn't exist.
        """
        def __init__(self):
            self.window_data = WindowHandle()
            
            self.pid = self.window_data.pid
            self.psutil = psutil.Process(self.pid)
        
        def __str__(self):
            return 'Process {} ({}): "{}" ({})'.format(self.pid, self.exe, self.name, '{}x{}'.format(*self.resolution))
    
        @property
        def rect(self):
            try:
                return self.window_data.rect
            except AttributeError:
                return (0, 0, 0, 0)
                
        @property
        def exe(self):
            """Get the name of the currently running process."""
            try:
                return self.window_data.exe
            except AttributeError:
                try:
                    return self.psutil.name()
                except psutil.NoSuchProcess:
                    return None
        
        @property
        def resolution(self):
            try:
                return self.window_data.resolution
            except AttributeError:
                x0, y0, x1, y1 = self.rect
                x_res = x1 - x0
                y_res = y1 - y0
                return (x_res, y_res)
        
        @property
        def name(self):
            try:
                return self.window_data.name
            except AttributeError:
                return True
        
        #Not in use but may have use later
        def percentage_memory_usage(self):
            try:
                return _get_memory_percent(self.psutil)
            except psutil.NoSuchProcess:
                return 0
        
        def memory_usage(self):
            try:
                memory_size = psutil.virtual_memory().total
            except psutil.NoSuchProcess:
                return 0
            return int(memory_size * self.percentage_memory_usage() / 100)
        
        def cmd_args(self):
            try:
                return self.psutil.cmdline()
            except psutil.NoSuchProcess:
                return None
            
        def working_directory(self):
            try:
                return self.psutil.cwd()
            except psutil.NoSuchProcess:
                return None
            
else:
    WindowFocus = None