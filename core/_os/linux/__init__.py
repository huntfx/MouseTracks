import os
import subprocess
import sys

try:
    from Xlib import display
except ImportError:
    sys.exit()

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

# returns an array of all currently running processes - the pid reading function will have
# to be added
def get_running_processes():
    pids = []
    program_list = subprocess.Popen('ps -d', shell=True, stdout=subprocess.PIPE).communicate()[0]
    for line in program_list.splitlines():
        line_ = line.decode()
        pids += line_
    return pids
