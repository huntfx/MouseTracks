# Determine which operating system is being used.
# A quick check will be one to make sure all the required modules exist
import platform
current_os = platform.system()

if current_os == 'Windows':
    try:
        from windows import *
    except ImportError:
        raise ImportError('no module found for windows')
if current_os == 'Linux':
    try:
        from linux import *
    except ImportError:
        raise ImportError('no module found for linux')
if current_os == 'Mac':
    try:
        from mac import *
    except ImportError:
        raise ImportError('no module found for mac')

try:
    get_resolution
    get_cursor_pos
    get_mouse_click
    get_key_press
    remove_file
    rename_file
    create_folder
    hide_file
    get_running_processes
except NameError:
    raise ImportError('missing modules for operating system')
