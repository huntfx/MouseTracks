"""
This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""

from __future__ import absolute_import, division

from re import sub
import os
import sys

from core.os import get_documents_path, read_env_var


def format_name(name, extra_chars=''):
    """Remove any invalid characters for file name."""
    return sub('[^A-Za-z0-9{}]+'.format(extra_chars), '', name).lower()
    

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