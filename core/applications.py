from __future__ import absolute_import
import time

from core.config import CONFIG
from core.constants import APP_LIST_URL
from core.notify import *
from core.files import format_file_path
from core.os import get_running_processes, WindowFocus
from core.internet import get_url_contents


APP_LIST_PATH = format_file_path(CONFIG['Paths']['AppList'])

_DEFAULT_TEXT = [
    '// Type any apps you want to be tracked here.',
    '// Two separate apps may have the same name, and will be tracked under the same file.',
    '// Put each app on a new line, in the format "Game.exe: Name".'
    ' The executable file is case sensitive.',
    '// Alternatively if the app is already named with the correct name'
    ', "Game.exe" by itself will use "Game" as its name.',
    ''
]

ALLOWED_EXTENSIONS = ['.exe', '.bin', '.app', '.scr', '.com']


def _format_app_text(app, friendly_name=None):

    #Ignore comments
    if not app or any(app.startswith(i) for i in ('#', ';', '/')):
        return None
        
    #Detect different extensions
    lowercase = app.lower()
    for i in ALLOWED_EXTENSIONS + [None]:
        if i is None:
            return i
        if i in lowercase:
            ext_len = len(lowercase.split(i)[0])
            app_name = '{}.{}'.format(app[:ext_len], app[ext_len + 1:ext_len + 4])
            break
    
    #Determine if name has been provided in file, or generate if not
    if friendly_name is None:
        try:
            friendly_name = app[ext_len:].split(':', 1)[1].strip()
        except IndexError:
            friendly_name = app[:ext_len]
        return (app_name, friendly_name)
    
    #Format line to save
    else:
        if app_name[:ext_len] == friendly_name:
            return app_name
        else:
            return '{}: {}'.format(app_name, friendly_name)
            
    return app

    
def _format_app_list(app_list):
    """Take a list of text inputs and sort them into a dictionary."""
    if isinstance(app_list, str):
        app_list = app_list.splitlines()
        
    applications = {}
    for app in app_list:
        
        app_info = _format_app_text(app.strip())
        if app_info is not None:
            app_name, friendly_name = app_info
            applications[app_name] = friendly_name
    
    return applications


def read_app_list(application_path=APP_LIST_PATH, allow_write=False):
    """Read the application list file.
    Optionally write a new one if it doesn't exist.
    """
    try:
        with open(application_path, 'r') as f:
            lines = f.readlines()
    except IOError:
        lines = _DEFAULT_TEXT + ['// game.exe: Name']
        if allow_write:
            with open(application_path, 'w') as f:
                f.write('\r\n'.join(lines))

    return _format_app_list(lines)

    
def download_app_list():
    """Download from the online application list.
    Requires the config to be set to allow internet access.
    """
    if not CONFIG['Internet']['Enable']:
        return None
    application_list_contents = get_url_contents(APP_LIST_URL)
    if application_list_contents:
        return _format_app_list(application_list_contents)
    return None


def update_app_list(applications, downloaded_applications=None):
    """Combine the current application list with the downloaded one."""
    if downloaded_applications is None:
        downloaded_applications = download_app_list()
    if downloaded_applications:
        for k, v in downloaded_applications.iteritems():
            if k not in applications:
                applications[k] = v
        return True
    return False
    

class RunningApplications(object):
    """Detect which applications are currently running."""

    def __init__(self, application_path=APP_LIST_PATH, queue=None):
        self.q = queue
        self.refresh()
        self.application_path = application_path
        self.reload_file()

    def reload_file(self):
    
        self.applications = read_app_list(self.application_path, allow_write=True)
        
        #Download from the internet and combine with the current list
        last_updated = CONFIG['SavedSettings']['AppListUpdate']
        update_frequency = CONFIG['Internet']['UpdateApplications']
        
        if not CONFIG['Internet']['Enable'] or not update_frequency:
            return
        
        #Only update if requirements are met
        next_update = time.time() - update_frequency
        if not self.applications or not last_updated or last_updated < next_update:
        
            if self.q is not None:
                NOTIFY(APPLIST_UPDATE_START)
                NOTIFY.send(self.q)
            
            if update_app_list(self.applications):
            
                CONFIG['SavedSettings']['AppListUpdate'] = int(time.time())
                CONFIG.save()
                self.save_file()
                
                if self.q is not None:
                    NOTIFY(APPLIST_UPDATE_SUCCESS)
            else:
                if self.q is not None:
                    NOTIFY(APPLIST_UPDATE_FAIL)
                    
            NOTIFY.send(self.q)
    
    def refresh(self):
        self.processes = get_running_processes()
        if WindowFocus is not None:
            self.focus = WindowFocus()
            self.focused_app = self.focus.exe()
        else:
            self.focus = None
    
    def save_file(self):
        lines = _DEFAULT_TEXT
        
        for app_info in sorted(self.applications.keys(), key=lambda s: s.lower()):
            
            friendly_name = self.applications[app_info]
            
            new_line = _format_app_text(app_info, friendly_name)
            if new_line is not None:
                lines.append(new_line)
        
        with open(self.application_path, 'w') as f:
            f.write('\n'.join(lines))
    

    def check(self):
        """Check for any applications in the list that are currently loaded.
        Check if any of them match the currently focused window (if applicable),
        or choose the one with the highest ID as it'll likely be the most recent one.
        """
        if self.focus is not None:
            try:
                return (self.applications[self.focused_app], self.focused_app)
            except KeyError:
                return None
        else:
            matching_applications = {}
            for application in self.applications:
                if application in self.processes:
                    matching_applications[self.processes[application]] = application
            if not matching_applications:
                return None
            latest_application = matching_applications[max(matching_applications.keys())]
            return (self.applications[latest_application], latest_application)
