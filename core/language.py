from locale import getdefaultlocale


system_language = getdefaultlocale()[0]
fallback_language = 'en_GB'

def open_language_file(language):
    with open('loc\\{}.txt'.format(language), 'r') as f:
        data = f.read()

    variables = {}
    for line in data.split('\n'):
        variable_name, variable_string = line.split('=', 1)
        variables[variable_name.strip()] = variable_string.strip()
    
    return variables
