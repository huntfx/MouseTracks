from constants import VERSION

VERSION_HISTORY = [
    '2.0',
    '2.0.1'
]

def upgrade_version(data):
    """Files from an older version will be run through this function."""
    get_id = VERSION_HISTORY.index
    
    current_version_id = VERSION_HISTORY.index(data['Version'])

    if current_version_id < get_id('2.0.1'):
        data['Acceleration'] = {}

    data['Version'] = VERSION
    return data
