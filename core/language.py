from locale import getdefaultlocale


system_language = getdefaultlocale()[0]
fallback_language = 'en_GB'

def _open_language_file(language):
    try:
        with open('loc\\{}.txt'.format(language), 'r') as f:
            data = f.read()
    except ImportError:
        return None

    variables = {}
    for line in data.split('\n'):
        variable_name, variable_string = line.split('=', 1)
        variables[variable_name.strip()] = variable_string.strip()
    
    return variables

    
def open_language_file(fallback_language='en_GB'):
    
    language_text = _open_language_file(system_language)
    if language_text is None:
        language_text = _open_language_file(fallback_language)

    return language_text
