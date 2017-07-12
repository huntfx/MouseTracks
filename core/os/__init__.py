# Determine which operating system is being used.
# A quick check will be one to make sure all the required modules exist
import platform
import os


#Load in modules from operating system
current_os = platform.system()
if current_os == 'Windows':
    try:
        from core.os.windows import *
    except ImportError:
        raise ImportError('missing modules for windows')
elif current_os == 'Linux':
    try:
        from core.os.linux import *
    except ImportError:
        raise ImportError('missing modules for linux')
elif current_os == 'Darwin':
    try:
        from core.os.mac import *
    except ImportError:
        raise ImportError('missing modules for mac')
else:
    raise ImportError('unknown operating system: "{}"'.format(current_os))


#Check the functions exist
try:
    get_cursor_pos
    get_mouse_click
    get_key_press
    hide_file
    get_running_processes
    get_resolution
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
        
except NameError:
    raise ImportError('missing functions for operating system')


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
    except (FileNotFoundError, WindowsError):
        return False
    return True


def rename_file(old_name, new_name):
    try:
        os.rename(old_name, new_name)
    except (FileNotFoundError, WindowsError):
        return False
    return True


def create_folder(folder_path):
    try:
        os.makedirs(folder_path)
    except (FileExistsError, WindowsError):
        return False
    return True

    
def get_modified_time(file_name):
    try:
        return os.path.getmtime(file_name)
    except (FileNotFoundError, WindowsError):
        return None
    
    
def list_directory(folder):
    try:
        return os.listdir(folder)
    except (FileNotFoundError, WindowsError):
        return None
