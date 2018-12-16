"""This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""
#Functions not specific to particular operating systems

from __future__ import absolute_import, division

import psutil
import os

from . import console


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
def split_folder_and_file(file_path, force_file=False, force_folder=False):
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

    
def is_file(file_name):
    return os.path.isfile(file_name)
    

def create_folder(folder_path, is_file=None):
    
    force_file = False if is_file is None else is_file
    force_folder = False if is_file is None else not is_file
    folder_path, file_path = split_folder_and_file(folder_path, force_file=force_file, force_folder=force_folder)
    
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


def get_file_size(path):
    return os.path.getsize(path)
    

def join_path(path, create=False):
    """Join a path, and create folder if needed."""
    joined = os.path.join(*path)
    if create:
        create_folder(joined)
    return joined


def open(path):
    """Open a file or folder from a path."""
    if not path:
        return False
    try:
        os.startfile(path)
    except (OSError, FileNotFoundError, WindowsError):
        return False
    return True
    
    
def open_folder(path):
    """Open a folder."""
    folder_path, file_path = split_folder_and_file(path)
    return open(folder_path)
    
    
def open_file(path):
    """Open a file."""
    folder_path, file_path = split_folder_and_file(path)
    if file_path is None:
        return False
    return open(path)


#Functions to be used with commands
def load_executable(path):
    
    folder_path, file_path = split_folder_and_file(path)
    
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
    

from ._load_from_os import *

    
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
            try:
                self.psutil = psutil.Process(self.pid)
            except (psutil.NoSuchProcess, ValueError):
                pass
        
        def __str__(self):
            return 'Process {} ({}): "{}" ({} at {})'.format(self.pid, self.exe, self.name, 
                                                             '{}x{}'.format(*self.resolution), 
                                                             '({}, {})'.format(*self.rect[:2]))
    
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
                except (psutil.NoSuchProcess, AttributeError):
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
            except (psutil.NoSuchProcess, AttributeError):
                return 0
        
        def memory_usage(self):
            try:
                memory_size = psutil.virtual_memory().total
            except (psutil.NoSuchProcess, AttributeError):
                return 0
            return int(memory_size * self.percentage_memory_usage() / 100)
        
        def cmd_args(self):
            try:
                return self.psutil.cmdline()
            except (psutil.NoSuchProcess, AttributeError):
                return None
            
        def working_directory(self):
            try:
                return self.psutil.cwd()
            except (psutil.NoSuchProcess, AttributeError):
                return None
            
else:
    WindowFocus = None