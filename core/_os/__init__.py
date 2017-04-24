# Determine which operating system is being used.
# A quick check will be one to make sure all the required modules exist

current_os = 'Windows'

if current_os == 'Windows':
    from windows import *
if current_os == 'Linux':
    from linux import *
if current_os == 'Mac':
    from mac import *

try:
    get_device_data
    get_cursor_pos
    get_mouse_click
    get_key_press
    remove_file
    rename_file
    create_folder
except NameError:
    raise ImportError('missing modules for operating system')
