from constants import VERSION

VERSION_HISTORY = [
    '2.0',
    '2.0.1'
]

def upgrade_version(data):
    """Files from an older version will be run through this function.

    History:
    2.0: Base script
    2.0.1: Add acceleration tracking
    """
    get_id = VERSION_HISTORY.index
    
    current_version_id = get_id(str(data['Version']))
    if current_version_id < get_id('2.0.1'):
        try:
            data['Acceleration']
        except KeyError:
            data['Acceleration'] = {}
            
    data['Version'] = VERSION
    return data
