from __future__ import absolute_import
import codecs

from core.config import CONFIG


ALLOWED_CHARACTERS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ_'

def open_language_file(language):

    try:
        with codecs.open('loc\\{}.txt'.format(language), 'r', 'utf-8') as f:
            data = f.read()
    except IOError:
        return None
    
    variables = {}
    for line in data.strip().split('\n'):
        if '=' in line:
            variable_name, variable_string = line.split('=', 1)
            variable_name = ''.join(i for i in variable_name if i in ALLOWED_CHARACTERS)
            variables[variable_name] = variable_string.strip()
    return variables

    
def get_language(fallback_language='en_GB'):
    """Try load the config language, or fallback to English."""
    language_text = open_language_file(CONFIG['Main']['Language'])
    if language_text is None:
        language_text = open_language_file(fallback_language)

    return language_text
