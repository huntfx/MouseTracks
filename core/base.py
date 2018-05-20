"""This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""
#Useful functions that require few imports but are widely used

from __future__ import absolute_import, division

import codecs
import os
import sys
from re import sub

from core.os import get_documents_path, read_env_var


def format_name(name, extra_chars=''):
    """Remove any invalid characters for file name."""
    try:
        return sub('[^A-Za-z0-9{}]+'.format(extra_chars), '', name).lower()
    except TypeError:
        if not isinstance(name, str):
            return format_name(str(name), extra_chars=extra_chars)
        raise
    

def format_file_path(path):
    """Process an input path and follow any environment variables."""
    
    #Set up any custom environment variables here
    custom_paths = {
        '%DOCUMENTS%': get_documents_path()
    }
    
    repeat = False
    parts = path.replace('\\', '/').rstrip('/').split('/')
    file_name = parts.pop(-1) if '.' in parts[-1] else None
    
    #Process each part separately
    for i, part in enumerate(parts):
        try:
            parts[i] = custom_paths[part]
        except KeyError:
            env_var = read_env_var(part)
            if env_var is not None:
                parts[i] = env_var
        else:
            if '%' in parts[i]:
                repeat = True
                
    if file_name is not None:
        parts.append(file_name)
    final_path = '/'.join(i.replace('\\', '/') for i in parts if i)
    
    if repeat:
        return format_file_path(final_path)
    return final_path
    
    
def get_script_path():
    return os.getcwd()

    #This has support for running from another folder, but may not always be correct
    return os.path.dirname(os.path.realpath(sys.argv[0]))
    

def get_script_file(file_name):
    return os.path.join(get_script_path(), file_name)


class TextFile(object):
    """Handle opening text files with different encodings."""

    UTF8_MARKER = chr(239) + chr(187) + chr(191)
    _UTF8_MARKER_LEN = len(UTF8_MARKER)
    UTF16_MARKER = chr(255) + chr(254)
    _UTF16_MARKER_LEN = len(UTF16_MARKER)
    
    def __init__(self, file_name, mode='r', encoding=None):
        self.file_name = file_name
        self.mode = mode.lower()
        self.encoding = encoding
        if self.encoding is not None:
            self.encoding = self.encoding.lower().replace('-', '')

    def __enter__(self):
        self.file_object = None

        #Check file header if reading
        if 'r' in self.mode:
            with open(self.file_name, self.mode) as f:
                header = f.read(3)
            if header.startswith(self.UTF8_MARKER):
                self.encoding = 'utf8'
            elif header.startswith(self.UTF16_MARKER):
                self.encoding = 'utf16'

        #Check valid encodings if writing
        if 'w' in self.mode:
            if self.encoding is not None and self.encoding not in ('utf8', 'utf16'):
                raise TypeError('unable to save with encoding "{}"'.format(self.encoding))

        #Load the file with a particular encoding
        if self.encoding is None:
            self.file_object = open(self.file_name, self.mode)
        else:
            self.file_object = codecs.open(self.file_name, self.mode, encoding=self.encoding)

        return self

    def __exit__(self, *args):
        self.file_object.close()
        return

    def readlines(self, unicode=True):
        return [self._process_output(line, index=i, unicode=unicode) 
                for i, line in enumerate(self.file_object.readlines())]

    def read(self, limit=-1):
        return self._process_output(self.file_object.read(limit), index=self.file_object.tell())

    def _process_output(self, output, index=None, unicode=True):
        """Handle different encodings to safely read the data.
        Currently UTF-8, UTF-16 and ANSI are supported.

        Setting unicode to False will force encode any unicode characters into 8 bytes.
        """
        output = output.strip()
        
        #Remove any known markers from the start of file
        if index is not None and not index:
            if self.encoding == 'utf8' and ord(output[0]) == 65279:
                output = output[1:]
        
        if self.encoding is not None and not unicode:
            output = output.encode('utf-8')
        
        return output.strip()

    def write(self, text, encoding=None):
        return self.file_object.write(text)