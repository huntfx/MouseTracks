import os
import subprocess
import re

try:
    from Xlib import display
except ImportError:
    raise NotImplemented('xlib not found')
try:
    import pyxhook
except ImportError:
    raise NotImplementedError('pyxhook not found')

# removes a file, NOT directory
def remove_file(file_name):
    try:
        os.remove(file_name)
    except FileNotFoundError:
        return False
    return True

# will only replace files and empty directories
def rename_file(old_name, new_name):
    try:
        os.replace(old_name, new_name)
    except FileNotFoundError:
        return False
    return True

def create_folder(folder_path):
    try:
        os.makedirs(folder_path)
    except FileExistsError:
        return False
    return True

def get_running_processes():
    pids = []
    program_list = subprocess.Popen('ps -d', shell=True, stdout=subprocess.PIPE).communicate()[0]
    for line in program_list.splitlines():
        line_ = line.decode()
        pids.append(line_)
    output = {line.rsplit()[-1] : line.rsplit()[0] for line in pids}
    return output

# returns a string
def get_refresh_rate():
    raw_rate = subprocess.Popen('xrandr | grep "\*" | cut -d" " -f9',shell=True, stdout=subprocess.PIPE).communicate()[0]
    Hz = re.search('\d+\.\d+', raw_rate.decode()).group()
    if Hz:
        return Hz
    else:
        return '60'

def get_resolution():
    d = display.Display().screen()
    return d.width_in_pixels, d.height_in_pixels

# should always return a tuple
def get_cursor_pos():
    d = display.Display().screen().root.query_pointer()
    return d.root_x, d.root_y
