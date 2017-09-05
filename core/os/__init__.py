# Determine which operating system is being used.
# A quick check will be one to make sure all the required modules exist
import platform
import os


def _add_placeholders(variables):
    """Use placeholder functions if the counterpart doesn't exist."""
    from core.os import placeholders
    count = 0
    for f_name in dir(placeholders):
        try: 
            variables[f_name]
        except KeyError:
            f = getattr(placeholders, f_name, None)
            if callable(f):
                variables[f_name] = f
                count += 1
    return count

                
#Load in modules from operating system
OPERATING_SYSTEM = platform.system()
if OPERATING_SYSTEM == 'Windows':
    try:
        from core.os.windows import *
    except ImportError:
        raise ImportError('missing required modules for windows')
    OS_DEBUG = False
elif OPERATING_SYSTEM == 'Linux':
    try:
        from core.os.linux import *
    except ImportError:
        raise ImportError('missing required modules for linux')
    OS_DEBUG = True
elif OPERATING_SYSTEM == 'Darwin':
    try:
        from core.os.mac import *
    except ImportError:
        raise ImportError('missing required modules for mac')
    OS_DEBUG = True
else:
    raise ImportError('unknown operating system: "{}"'.format(OPERATING_SYSTEM))

PLACEHOLDER_COUNT = _add_placeholders(locals())


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
    
    #Detect if code exists to detect window focus
    try:
        WindowFocusData
        import psutil
        FOCUS_DETECTION = True
    except (ImportError, NameError):
        FOCUS_DETECTION = False
        
        
except NameError:
    raise ImportError('failed to import all required modules')


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
    except (OSError, FileNotFoundError, WindowsError):
        return False
    return True


def rename_file(old_name, new_name):
    try:
        os.rename(old_name, new_name)
    except (OSError, FileNotFoundError, WindowsError):
        return False
    return True


def create_folder(folder_path):
    
    #Remove file from path
    folders = folder_path.replace('\\', '/').split('/')
    if not folders[-1] or '.' in folders[-1][1:]:
        folder_path = '/'.join(folders[:-1])
    
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
    
    
def list_directory(folder):
    try:
        return os.listdir(folder)
    except (OSError, FileNotFoundError, WindowsError):
        return None


if FOCUS_DETECTION:
    
    class WindowFocus(object):
        def __init__(self):
            self.window_data = WindowFocusData()
    
        def pid(self):
            """Get the process ID of the focused window."""
            return self.window_data.get_pid()
        
        def exe(self):
            """Get the name of the currently running process."""
            try:
                return self.window_data.get_exe()
            except AttributeError:
                return psutil.Process(self.pid()).name()
        
        def rect(self):
            """Get the corner coordinates of the focused window."""
            return self.window_data.get_rect()
        
        def resolution(self):
            try:
                return self.window_data.get_resolution()
            except AttributeError:
                x0, y0, x1, y1 = self.rect()
                x_res = x1 - x0
                y_res = y1 - y0
                return (x_res, y_res)
        
        def name(self):
            try:
                return self.window_data.get_name()
            except AttributeError:
                return True
        
else:
    WindowFocus = None
