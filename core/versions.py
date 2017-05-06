VERSION_HISTORY = [
    '2.0',
    '2.0.1',
    '2.0.1b'
]
VERSION = VERSION_HISTORY[-1]

def upgrade_version(data):
    """Files from an older version will be run through this function.

    History:
    2.0: Base script
    2.0.1: Add acceleration tracking
    2.0.1b: Rename acceleration to speed, change tracking method
    """
    get_id = VERSION_HISTORY.index
    
    current_version_id = get_id(str(data['Version']))
    if current_version_id < get_id('2.0.1'):
        data['Acceleration'] = {}
    if current_version_id < get_id('2.0.1b'):
        try:
            del data['Acceleration']
        except KeyError:
            pass
        data['Speed'] = {}
    
    data['Version'] = VERSION
    return data
