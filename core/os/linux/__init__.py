import os
import subprocess
import re

try:
    from core.os.linux.linux_xlib import *
except ImportError:
    raise ImportError('required modules not found')


def remove_file(file_name):
    try:
        os.remove(file_name)
    except FileNotFoundError:
        return False
    return True


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
    output = {line.rsplit()[-1]: line.rsplit()[0] for line in pids}
    return output


def get_refresh_rate():
    raw_rate = subprocess.Popen('xrandr | grep "\*" | cut -d" " -f9',shell=True, stdout=subprocess.PIPE).communicate()[0]
    refresh_rate = re.search('\d+\.\d+', raw_rate.decode()).group()
    if refresh_rate:
        return int(refresh_rate)
    else:
        return None


#Placeholder functions
KEYS = {}
def get_key_press(key):
    return False
def show_file(file_name):
    pass
def hide_file(file_name):
    pass
