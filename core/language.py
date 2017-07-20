from __future__ import absolute_import
from locale import getdefaultlocale
import codecs

from core.config import CONFIG


ALLOWED_CHARACTERS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ_'

LANGUAGE_FOLDER = 'loc'

KEYBOARD_LAYOUT_FOLDER = 'kb'

STRINGS_FOLDER = 'str'


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

    def __init__(self, language=CONFIG['Main']['Language'], fallback_language='en_GB'):
        self.strings = None
        self.keyboard = None
    
        #Read from main file
        links = follow_file_links(language, 'txt', LANGUAGE_FOLDER)
        for link in links:
            if link.startswith('STRINGS'):
                self.strings = link.split('=', 1)[1].strip()
            if link.startswith('KEYBOARD_LAYOUT'):
                self.keyboard = link.split('=', 1)[1].strip()
        
        #Read from backup file
        if self.strings is None or self.keyboard is None:
            links = follow_file_links(fallback_language, 'txt', LANGUAGE_FOLDER)
            for link in links:
                if self.strings is None and link.startswith('STRINGS'):
                    self.strings = link.split('=', 1)[1].strip()
                if self.keyboard is None and link.startswith('KEYBOARD_LAYOUT'):
                    self.keyboard = link.split('=', 1)[1].strip()
                
        
    def get_keyboard_layout(self):
        keyboard_layout = []
        
        try:
            data = follow_file_links(self.keyboard, 'txt', '{}/{}'.format(LANGUAGE_FOLDER, KEYBOARD_LAYOUT_FOLDER))
        except AttributeError:
            return []
            
        try:
            gap = float(data[0])
        except ValueError:
            gap = 1
        else:
            del data[0]
            
        for row in data:
            for key in row.split('+'):
            
                key_data = key.split('|')
                default_height = 1
                default_width = 1
                
                #Get key name if set, otherwise change the width
                try:
                    name = key_data[0]
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
                try:
                    height = float(key_data[1])
                except (IndexError, ValueError):
                    height = default_height
                
                keyboard_layout.append([name, width, height])
                
        return keyboard_layout
    
    def get_strings(self):
        try:
            data = follow_file_links(self.strings, 'txt', '{}/{}'.format(LANGUAGE_FOLDER, STRINGS_FOLDER))
        except AttributeError:
            return {}
        strings = {}
        for line in data:
            if '=' in line:
                name, string = line.split('=', 1)
                name = ''.join(i for i in name if i in ALLOWED_CHARACTERS)
                strings[name] = string.strip()
        return strings
