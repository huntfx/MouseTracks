from __future__ import absolute_import

from core.config import CONFIG


def open_language_file(language):
    try:
        with open('loc\\{}.txt'.format(language), 'r') as f:
            data = f.read()
    except ImportError:
        return None

    variables = {}
    for line in data.split('\n'):
        if '=' in line:
            variable_name, variable_string = line.split('=', 1)
            variables[variable_name.strip()] = variable_string.strip()
    
    return variables

    
def get_language(fallback_language='en_GB'):
    """Try load the config language, or fallback to English."""
    language_text = open_language_file(CONFIG['Main']['Language'])
    if language_text is None:
        language_text = open_language_file(fallback_language)

    return language_text
