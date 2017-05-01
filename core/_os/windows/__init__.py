try:
    from win_api import *
except ImportError:
    from win_ctypes import *

def remove_file(file_name):
    """Delete a file.
    Returns:
        True/False if successful or not.
    """
    try:
        os.remove(file_name)
    except WindowsError:
        return False
    return True


def rename_file(old_name, new_name):
    """Rename a file.
    Return:
        True/False if successful or not.
    """
    try:
        os.rename(old_name, new_name)
    except WindowsError:
        return False
    return True


def create_folder(folder_path):
    """Create a folder.
    Return:
        True/False if successful or not.
    """
    try:
        os.makedirs(folder_path)
    except WindowsError:
        return False
    return True
