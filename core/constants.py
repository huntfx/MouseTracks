from __future__ import division, absolute_import

from core.os import get_documents_path, read_env_var


DEFAULT_NAME = 'Default'

DEFAULT_PATH = '%DOCUMENTS%\\Mouse Tracks'

CONFIG_PATH = '{}\\config.ini'.format(DEFAULT_PATH)

APP_LIST_URL = 'https://raw.githubusercontent.com/Peter92/MouseTrack/master/AppList.txt'

DEFAULT_LANGUAGE = 'en_US'


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
