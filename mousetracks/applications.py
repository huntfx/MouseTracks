"""This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""
#Check for running applications using AppList.txt

from __future__ import absolute_import

import re
import time

from .config.settings import CONFIG
from .config.language import LANGUAGE
from .constants import APP_LIST_URL, UPDATES_PER_SECOND, TRACKING_DISABLE, TRACKING_IGNORE, TRACKING_WILDCARD
from .misc import TextFile
from .notify import NOTIFY
from .files import format_file_path
from .utils.compatibility import iteritems, unicode
from .utils.os import get_running_processes, WindowFocus, get_modified_time, split_folder_and_file
from .utils.internet import get_url_contents


RECOGNISED_EXTENSIONS = ['exe', 'bin', 'app', 'scr', 'com']

APP_LIST_PATH = format_file_path(CONFIG['Paths']['AppList'])

_DEFAULT_TEXT = [
    '// Add any applications you want to be tracked here.',
    '// Two separate applications can have the same name,'
    ' and will be tracked under the same file.',
    '// Put each app on a new line, in the format "MyGame.exe: Game Name".'
    ' The executable file is case sensitive.',
    '// You may also limit it to a certain window name,'
    ' for example if the game uses a generic executable name.',
    '// This would work like "Play.exe[MyGame]: Game Name". You may use "{}" at the start or end of "MyGame" as a wildcard.'.format(TRACKING_WILDCARD),
    '// If the executable or window name is the same as the game name,'
    ' you only need to provide that.',
    '// To turn off tracking for a particular application, use "{}" as its name.'.format(TRACKING_DISABLE),
    '// To ignore tracking when a window name is a match (such as a splash screen), use "{}" as its name.'.format(TRACKING_IGNORE)
]

_WILDCARD_LEN = len(TRACKING_WILDCARD)


class AppList(object):
    def __init__(self, path=APP_LIST_PATH):
        self.path = path
        self.folder, self.name = split_folder_and_file(path, force_file=True)

        extensions = ['.'+i for i in RECOGNISED_EXTENSIONS]
        self.extensions = {i: {'len': len(i), ':': i+':', '[': i+'['}
                           for i in extensions}
        
        self.refresh()
        
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
                
            #Read file from URL
            try:
                lines = get_url_contents(url).decode('utf-8').split('\n')
            except AttributeError:
                return {}
                
        else:
            #Read from script directory
            try:
                with TextFile(path.replace('\\', '/').split('/')[-1], 'r', encoding='utf-8') as f:
                    lines = [i.strip() for i in f.readlines()]
            except IOError:
                lines = []
                
            #Read from documents
            try:
                with TextFile(path, 'r', encoding='utf-8') as f:
                    lines += [i.strip() for i in f.readlines()]
            except IOError:
                if not lines:
                    return {}

        executable_files = {}
        for line in lines:
                        
            #Ignore comments
            if line.startswith('//'):
                continue

            #Check for each extensions
            #TODO: Allow no extension, such as hl2_osx in OSX
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
                            game_name = window_name.replace(TRACKING_WILDCARD, '').strip()

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
        
        #Build list of names
        self.names = []
        for v in self.data.values():
            for name in v.values():
                self.names.append(name)

    def save(self, path=None):
        """Save the sorted application list."""
        result = []
        for executable, names in iteritems(self.data):
            for ext in self.extensions:
                if executable.lower().endswith(ext):
                    for window_name, app_name in iteritems(names):
                        if window_name is None:
                            if app_name == executable[:-self.extensions[ext]['len']]:
                                result.append(unicode(executable))
                            else:
                                result.append(u'{}: {}'.format(executable, app_name))
                        else:
                            if window_name == app_name:
                                result.append(u'{}[{}]'.format(executable, window_name))
                            else:
                                result.append(u'{}[{}]: {}'.format(executable, window_name, app_name))
                    break
        result = '\r\n'.join(_DEFAULT_TEXT + [''] + sorted(result, key=unicode.lower))
        
        if path is None:
            path = self.path
        with TextFile(path, 'wb', encoding='utf-8') as f:
            f.write(result.encode('utf-8'))
        return result

    def update(self, url=APP_LIST_URL, save=True):
        """Update application list from URL.
        Does not overwrite any values.
        """
        url_data = self._read(url=url)
        if not url_data:
            return False
        for executable, names in iteritems(url_data):
            if executable not in self.data:
                self.data[executable] = url_data[executable]
            else:
                for name in names:
                    if name not in self.data[executable]:
                        self.data[executable][name] = names[name]
        if save:
            self.save(self.path)
        return True

    @property
    def executables(self):
        return self.data.keys()
        

class RunningApplications(object):
    """Detect which applications are currently running."""

    def __init__(self, application_path=APP_LIST_PATH, queue=None):
        self.q = queue
        self.applist = AppList(application_path)
        self.refresh()
        self.reload_file()
        self._regex_cache = {}

    def reload_file(self):
        #Download from the internet and combine with the current list
        last_updated = get_modified_time(APP_LIST_PATH)
        update_frequency = CONFIG['Internet']['UpdateApplications'] * UPDATES_PER_SECOND
        
        if not CONFIG['Internet']['Enable'] or not update_frequency:
            return
        
        #Only update if requirements are met
        next_update = time.time() - update_frequency
        if not self.applist or not last_updated or last_updated < next_update:
        
            NOTIFY(LANGUAGE.strings['Tracking']['ApplistDownloadStart'], FILE_NAME=self.applist.name, URL=APP_LIST_URL).put(self.q)
            if self.applist.update(APP_LIST_URL):
                self.applist.save()
                NOTIFY(LANGUAGE.strings['Tracking']['ApplistDownloadSuccess'], FILE_NAME=self.applist.name, URL=APP_LIST_URL)
            else:
                NOTIFY(LANGUAGE.strings['Tracking']['ApplistDownloadFail'], FILE_NAME=self.applist.name, URL=APP_LIST_URL)
            NOTIFY.put(self.q)
        
    def refresh(self):
        """Get list of currently running programs and focused window."""
        if WindowFocus is None:
            self.focus = None
            self.processes = get_running_processes()
        else:
            self.focus = WindowFocus()
            self.focused_exe = self.focus.exe
            self.focused_name = self.focus.name

    def all_loaded_apps(self):
        """Get list of every loaded program."""
        loaded = []
        
        #Get dict of running processes here if focus is enabled
        if WindowFocus is not None:
            self.processes = get_running_processes()
        
        matching_applications = {self.processes[app]: app
                                 for app in self.applist
                                 if app in self.processes}
        
        for index in sorted(matching_applications.keys())[::-1]:
            loaded_exe = matching_applications[index]
            names = self.applist[loaded_exe]
            try:
                loaded.append(names[None])

            #Only fallback to window name if it is the only entry for that application
            except KeyError:
                if len(names) == 1 or len(set(names.values())) == 1:
                    loaded.append(names[tuple(names.keys())[0]])
        return set(loaded)
            
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
                #Otherwise we don't know which entry to use, so ignore
                except KeyError:
                    if len(names) == 1 or len(set(names.values())) == 1:
                        return names[tuple(names.keys())[0]], loaded_exe
            return None

        #Get currently focused application
        elif self.focused_exe in self.applist:
            names = self.applist[self.focused_exe]

            #Check if record exists for current window name
            try:
                return names[self.focused_name], self.focused_exe
            except KeyError:
                try:
                    #Check for wildcard at start and end of window name
                    for name in names:
                        if name is None:
                            continue
                        
                        #Use regex if wildcard in name
                        if TRACKING_WILDCARD in name:
                            try:
                                regex = self._regex_cache[name]
                            except KeyError:
                                pattern = name.replace(TRACKING_WILDCARD, '(.*)')
                                regex = re.compile(pattern)
                                self._regex_cache[name] = regex

                            match = regex.search(self.focused_name) is not None
                        
                        else:
                           match = name == self.focused_name
                            
                        if match:
                            return names[name], self.focused_exe

                    #Return default name
                    return names[None], self.focused_exe

                #Default name doesn't exist
                except KeyError:
                    return None

    def save_file(self):
        self.applist.save()