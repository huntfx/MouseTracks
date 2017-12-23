"""
This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""

from __future__ import absolute_import

import codecs

import core.utf8
from core.base import get_script_file
from core.config import CONFIG
from core.constants import DEFAULT_LANGUAGE


ALLOWED_CHARACTERS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_'

LANGUAGE_FOLDER = 'language'

KEYBOARD_LAYOUT_FOLDER = 'keyboard_layout'

CONSOLE_STRINGS_FOLDER = 'console'

LANGUAGE_BASE_PATH = get_script_file(LANGUAGE_FOLDER)


def follow_file_links(file_name, extension, path, visited=None):
    """Follow paths recursively if they contain a link to another file."""
    
    #Check for recursion
    if visited is None:
        visited = set()
    if file_name in visited:
        raise IOError('recursion in file links')
    visited.add(file_name)
    
    #Read the file
    try:
        with codecs.open('{}/{}.{}'.format(path, file_name, extension), 'r', 'utf-8') as f:
            read_data = f.read()
            if ord(read_data[0]) == 65279: #Remove dumb utf-8 marker that won't disappear
                read_data = read_data[1:]
            data = read_data.strip().splitlines()
    except IOError:
        data = []
    else:
        if data and data[0][0].lstrip() == '<' and data[0][-1].rstrip() == '>':
            return follow_file_links(data[0][1:-1], extension, path, visited)
    return data


class Language(object):

    def __init__(self, language=CONFIG['Main']['Language'], fallback_language=DEFAULT_LANGUAGE):
        self.strings = None
        self.keyboard = None
    
        #Read from chosen file, then backup file if needed
        language_order = (language, fallback_language)
        for language in language_order:
        
            links = follow_file_links(language, 'txt', LANGUAGE_BASE_PATH)
            for link in links:
                var, value = [i.strip() for i in link.split('=')]
                link_parts = var.split('.')
                if link_parts[0] == 'locale':
                    if link_parts[1] == 'strings':
                        self.strings = link.split('=', 1)[1].strip()
                    elif link_parts[1] == 'keyboard':
                        if link_parts[2] == 'layout':
                            self.keyboard = link.split('=', 1)[1].strip()
            if self.strings is not None and self.keyboard is not None:
                break
        
        if self.strings is None or self.keyboard is None:
            raise IOError('no language file found in the folder "{}\\"'.format(LANGUAGE_BASE_PATH))
                
        
    def get_keyboard_layout(self, extended=True):
        keyboard_layout = []
        
        keyboard_layout_folder = '{}/{}'.format(LANGUAGE_BASE_PATH, KEYBOARD_LAYOUT_FOLDER)
        try:
            data = follow_file_links(self.keyboard, 'txt', keyboard_layout_folder)
        except AttributeError:
            return []
            
        try:
            gap = float(data[0])
        except ValueError:
            gap = 1
        else:
            del data[0]
        
        data_len = len(data)
        for i, row in enumerate(data):
            keyboard_layout.append([])
            
            #Handle half rows
            row = row.strip()
            if not row:
                continue
            
            #Remove second half of keyboard if required
            if extended:
                row = row.replace(':', '')
            else:
                row = row.split(':', 1)[0]
            
            for key in row.split('+'):
            
                key_data = key.split('|')
                default_height = 1
                default_width = 1
                
                #Get key name if set, otherwise change the width
                try:
                    name = str(key_data[0])
                    if not name:
                        name = None
                        raise IndexError
                except IndexError:
                    default_width = gap
                
                #Set width and height
                try:
                    width = float(key_data[1])
                except (IndexError, ValueError):
                    width = default_width
                else:
                    width = max(0, width)
                try:
                    height = float(key_data[2])
                except (IndexError, ValueError):
                    height = default_height
                else:
                    height = max(0, height)
                
                keyboard_layout[-1].append([name, width, height])
                
        return keyboard_layout
    
    def get_strings(self):
        try:
            data = follow_file_links(self.strings, 'txt', '{}/{}'.format(LANGUAGE_BASE_PATH, CONSOLE_STRINGS_FOLDER))
        except AttributeError:
            return {}
        strings = {}
        
        for line in data:
            try:
                var, value = [i.strip() for i in line.split('=', 1)]
            except ValueError:
                pass
            else:
                var_parts = var.split('.')
                var_len = len(var_parts)
                if var_len == 1:
                    continue
                
                #Recursively look down dictionary
                _strings = strings
                for i, part in enumerate(var_parts[:-1]):
                    last_loop = i == var_len - 2
                    try:
                        if not last_loop:
                            _strings = _strings[part]
                    except KeyError:
                        _strings[part] = {}
                        if not last_loop:
                            _strings = _strings[part]
                        
                try:
                    _strings[part][var_parts[-1]] = value.replace('\\n', '\n')
                except KeyError:
                    _strings[part] = {var_parts[-1]: value.replace('\\n', '\n')}
        
        return strings
