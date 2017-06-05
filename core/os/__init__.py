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
        raise ImportError('no module found for windows')
elif current_os == 'Linux':
    try:
        from core.os.linux import *
    except ImportError:
        raise ImportError('no module found for linux')
elif current_os == 'Mac':
    try:
        from core.os.mac import *
    except ImportError:
        raise ImportError('no module found for mac')
else:
    raise ImportError('unknown operating system: "{}"'.format(current_os))


#Check the functions exist
try:
    get_cursor_pos
    get_mouse_click
    get_key_press
    remove_file
    rename_file
    create_folder
    hide_file
    get_running_processes
    
    #Detect if code should use multiple monitors
    #Don't check the length as it's possible a monitor can be plugged in later
    try:
        monitor_info = get_monitor_locations
        MULTI_MONITOR = True
    except NameError:
        monitor_info = get_resolution
        MULTI_MONITOR = False
        
except NameError:
    raise ImportError('missing modules for operating system')
    

def get_modified_time(file_name):
    return os.path.getmtime(file_name)


def get_folder_contents(path):
    return os.listdir(path)
