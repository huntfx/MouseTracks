from __future__ import absolute_import
import time

from core.compatibility import get_items
from core.config import CONFIG
from core.constants import APP_LIST_URL
from core.notify import *
from core.files import format_file_path
from core.os import get_running_processes, WindowFocus
from core.internet import get_url_contents


RECOGNISED_EXTENSIONS = ['exe', 'bin', 'app', 'scr', 'com']

APP_LIST_PATH = format_file_path(CONFIG['Paths']['AppList'])

_ENCODINGS = [''.join(chr(i) for i in (239, 187, 191))]

_DEFAULT_TEXT = [
    '// Add any applications you want to be tracked here.',
    '// Two separate applications can have the same name,'
    ' and will be tracked under the same file.',
    '// Put each app on a new line, in the format "MyGame.exe: Game Name".'
    ' The executable file is case sensitive.',
    '// You may also limit it to a certain window name,'
    ' for example if the game uses a generic executable name.',
    '// This would work like "Play.exe[MyGame]: Game Name".',
    '// If the executable or window name is the same as the game name,'
    ' you only need to provide that.'
]


class AppList(object):
    def __init__(self, path=APP_LIST_PATH):
        self.path = path

        extensions = ['.'+i for i in RECOGNISED_EXTENSIONS]
        self.extensions = {i: {'len': len(i), ':': i+':', '[': i+'['}
                           for i in extensions}
        
        self.refresh()

    def _read(self, path=None, url=None):
        """Parse an application list and return a dictionary.

        Accepted formats:
            MyGame.exe
            MyGame.exe: Game Name
            MyGame.exe[Window Name]
            MyGame.exe[Window Name]: Game Name
        """
        if path is None:
            if url is None:
                return {}
            try:
                lines = get_url_contents(path).split('\n')
            except AttributeError:
                return {}
                
        else:
            with open(path, 'r') as f:
                lines = [i.strip() for i in f.readlines()]
            
        for marker in _ENCODINGS:
            if lines[0].startswith(marker):
                lines[0] = lines[0][len(marker):]
                break

        executable_files = {}
        for line in lines:
                        
            #Ignore comments
            if line.startswith('//'):
                continue

            #Check for each extensions
            no_space = line.replace(' ', '').lower()
            for ext in self.extensions:
                if ext in no_space:

                    #In the format "MyGame.exe: Game Name"
                    if self.extensions[ext][':'] in no_space:
                        executable_name, game_name = line.split(':', 1)
                        window_name = None

                    #In the format "MyGame.exe[Window Name]"
                    #or "MyGame.exe[Window Name]: Game Name"
                    elif self.extensions[ext]['['] in no_space:
                        executable_name, remaining = line.split('[', 1)
                        window_name, remaining = remaining.split(']', 1)
                        if remaining.strip().startswith(':'):
                            game_name = remaining.split(':', 1)[1]
                        else:
                            game_name = window_name

                    #In the format "MyGame.exe"
                    elif no_space.endswith(ext):
                        executable_name = line
                        window_name = None
                        game_name = line[:-self.extensions[ext]['len']]
                    else:
                        continue
                    
                    try:
                        executable_files[executable_name.strip()][window_name] = game_name.strip()
                    except KeyError:
                        executable_files[executable_name.strip()] = {window_name: game_name.strip()}
                    
        return executable_files

    def refresh(self):
        """Get data from the file."""
        self.data = self._read(self.path)

    def save(self, path=None):
        """Save the sorted application list."""
        result = []
        for executable, names in get_items(self.data):
            for ext in self.extensions:
                if executable.lower().endswith(ext):
                    for window_name, app_name in get_items(names):
                        if window_name is None:
                            if app_name == executable[:-self.extensions[ext]['len']]:
                                result.append(executable)
                            else:
                                result.append('{}: {}'.format(executable, app_name))
                        else:
                            if window_name == app_name:
                                result.append('{}[{}]'.format(executable, window_name))
                            else:
                                result.append('{}[{}]: {}'.format(executable, window_name, app_name))
                    break
        result = '\n'.join(_DEFAULT_TEXT + [''] + sorted(result, key=str.lower))
        
        if path is None:
            path = self.path
        with open(path, 'w') as f:
            f.write(result)
        return result

    def update(self, url):
        """Update application list from URL.
        Does not overwrite any values.
        """
        url_data = self._read(url=url)
        if not url_data:
            return False
        for executable, names in get_items(url_data):
            if executable not in self.data:
                self.data[executable] = url_data[executable]
            else:
                for name in names:
                    if name not in self.data[executable]:
                        self.data[executable][name] = names[name]
        return True
        
    def __getitem__(self, key):
        return self.data[key]
        
    def __setitem__(self, key, value):
        self.data[key] = value

    def __delitem__(self, key):
        del self.data[key]

    def __contains__(self, key):
        return key in self.data

    def __iter__(self):
        return self.data.keys().__iter__()

    def __str__(self):
        return str(self.data)

    def __nonzero__(self):
        return bool(self.data)

    def __bool__(self):
        return bool(self.data)

    def pop(self, n):
        return self.data.pop(n)
        

class RunningApplications(object):
    """Detect which applications are currently running."""

    def __init__(self, application_path=APP_LIST_PATH, queue=None):
        self.q = queue
        self.applist = AppList(application_path)
        self.refresh()
        self.reload_file()

    def reload_file(self):
        #Download from the internet and combine with the current list
        last_updated = CONFIG['SavedSettings']['AppListUpdate']
        update_frequency = CONFIG['Internet']['UpdateApplications'] * 60
        
        if not CONFIG['Internet']['Enable'] or not update_frequency:
            return
        
        #Only update if requirements are met
        next_update = time.time() - update_frequency
        if not self.applist or not last_updated or last_updated < next_update:
        
            if self.q is not None:
                NOTIFY(APPLIST_UPDATE_START)
                NOTIFY.send(self.q)
                
            if self.applist.update(APP_LIST_URL):
                CONFIG['SavedSettings']['AppListUpdate'] = int(time.time())
                CONFIG.save()
                self.applist.save()
                
                if self.q is not None:
                    NOTIFY(APPLIST_UPDATE_SUCCESS)
            else:
                if self.q is not None:
                    NOTIFY(APPLIST_UPDATE_FAIL)
                    
            NOTIFY.send(self.q)
        
    def refresh(self):
        """Get list of currently running programs and focused window."""
        if WindowFocus is None:
            self.focus = None
            self.processes = get_running_processes()
        else:
            self.focus = WindowFocus()
            self.focused_exe = self.focus.exe()
            self.focused_name = self.focus.name()

    def check(self):
        """Return the name and executable of a running application."""
        #Get most recently loaded application
        if self.focus is None:
            
            matching_applications = {self.processes[app]: app
                                     for app in self.applist
                                     if app in self.processes}
            
            for index in sorted(matching_applications.keys())[::-1]:
                loaded_exe = matching_applications[index]
                names = self.applist[loaded_exe]
                try:
                    return names[None], loaded_exe

                #Only fallback to window name if it is the only entry for that application
                except KeyError:
                    if len(names) == 1 or len(set(names.values())) == 1:
                        return names[names.keys()[0]], loaded_exe
            return None

        #Get currently focused application
        else:
            if self.focused_exe in self.applist:
                names = self.applist[self.focused_exe]
                try:
                    return names[self.focused_name], self.focused_exe
                except KeyError:
                    try:
                        return names[None], self.focused_exe
                    except KeyError:
                        return None
    
    def save_file(self):
        self.applist.save()

