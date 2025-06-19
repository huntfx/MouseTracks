"""This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""
#Useful functions that require few imports but are widely used

from __future__ import absolute_import, division

import codecs
import os
import sys
import zipfile
from re import sub

from .utils.compatibility import PYTHON_VERSION, BytesIO, unicode
from .utils.os import get_documents_path, read_env_var


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
    if hasattr(sys, '_MEIPASS'):
        return sys._MEIPASS
    return os.getcwd()

    #This has support for running from another folder, but may not always be correct
    return os.path.dirname(os.path.realpath(sys.argv[0]))
    

def get_config_file(file_name):
    return os.path.join(get_script_path(), 'config', file_name)


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
            if PYTHON_VERSION < 3:
                with codecs.open(self.file_name, self.mode) as f:
                    header = f.read(3)
            else:
                with codecs.open(self.file_name, self.mode, encoding='ansi') as f:
                    header = f.read(3)
            if header.startswith(self.UTF8_MARKER):
                self.encoding = 'utf8'
            elif header.startswith(self.UTF16_MARKER):
                self.encoding = 'utf16'
            else:
                self.encoding = 'utf8'

        #Check valid encodings if writing
        if 'w' in self.mode:
            if self.encoding is not None and self.encoding not in ('utf8', 'utf16'):
                raise TypeError('unable to save with encoding "{}"'.format(self.encoding))

        #Load the file with a particular encoding
        if self.encoding is None:
            if PYTHON_VERSION < 3:
                self.file_object = codecs.open(self.file_name, self.mode)
            else:
                self.file_object = codecs.open(self.file_name, self.mode, encoding='ansi')
        else:
            self.file_object = codecs.open(self.file_name, self.mode, encoding=self.encoding)

        return self

    def __exit__(self, *args):
        self.file_object.close()
        return

    def readlines(self, as_unicode=True):
        return [self._process_output(line, index=i, as_unicode=as_unicode) 
                for i, line in enumerate(self.file_object.readlines())]

    def read(self, limit=-1):
        return self._process_output(self.file_object.read(limit), index=self.file_object.tell())

    def _process_output(self, output, index=None, as_unicode=True):
        """Handle different encodings to safely read the data.
        Currently UTF-8, UTF-16 and ANSI are supported.

        Setting as_unicode to False will force encode any unicode characters into 8 bytes.
        Seems important for Python 2, but not so much for Python 3.
        """
        output = output.strip()
        
        #Remove any known markers from the start of file
        if index is not None and not index:
            if self.encoding == 'utf8' and ord(output[0]) == 65279:
                output = output[1:]
        
        if self.encoding is not None and not as_unicode:
            output = output.encode('utf8')
        
        output = output.strip()

        #Convert bytes to string if Python 3 (causes crash on Python 2)
        if PYTHON_VERSION == 2:
            return output
        return str(output)

    def write(self, text, encoding=None):
        if encoding is None:
            encoding = self.encoding
        if encoding:
            return self.file_object.write(text.decode(encoding))
        return self.file_object.write(text)


class CustomOpen(object):
    """Wrapper containing the default "open" function alongside the "zipfile" one.
    This allows for a lot cleaner method of reading a file that may or may not be a zip.
    """
    
    def __init__(self, filename=None, mode='r', as_zip=True):

        self.file = filename        
        if self.file is None:
            self.mode = 'w'
        else:
            self.mode = mode

        #Attempt to open as zip, or fallback to normal if invalid
        if as_zip:
            if self.mode.startswith('r'):
                try:
                    self._file_object = None
                    self.zip = zipfile.ZipFile(self.file, 'r')
                except zipfile.BadZipfile:
                    as_zip = False
            else:
                if self.file is None:
                    self._file_object = BytesIO()
                    self.zip = zipfile.ZipFile(self._file_object, 'w', zipfile.ZIP_DEFLATED)
                else:
                    self._file_object = None
                    self.zip = zipfile.ZipFile(self.file, 'w', zipfile.ZIP_DEFLATED)

        #Open as normal file
        if not as_zip:
            self.zip = None
            if self.mode.startswith('r'):
                self._file_object = open(self.file, mode=self.mode)
            else:
                self._file_object = BytesIO()
        
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        """Close the file objects and save file if a name was given."""
        if self.zip is not None:
            self.zip.close()
        if self.mode == 'w' and self.file is not None and self._file_object is not None:
            with open(self.file, 'wb') as f:
                f.write(self._file_object.getvalue())
        if self._file_object is not None:
            self._file_object.close()
        
    def read(self, filename=None, seek=0):
        """Read the file."""
        self.seek(seek)
        if self.zip is None:
            return self._file_object.read()
        return self.zip.read(str(filename))

    def write(self, data, filename=None):
        """Write to the file."""
        if self.zip is None:
            if isinstance(data, (str, unicode)):
                return self._file_object.write(data.encode('utf-8'))
            return self._file_object.write(data)
        if filename is None:
            raise TypeError('filename required when writing to zip')
        return self.zip.writestr(str(filename), data)
 
    def seek(self, amount):
        """Seek to a certain point of the file."""
        if amount is None or self._file_object is None:
            return
        return self._file_object.seek(amount)