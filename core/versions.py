VERSION_HISTORY = [
    '2.0',
    '2.0.1',
    '2.0.1b',
    '2.0.2'
]
VERSION = VERSION_HISTORY[-1]

def upgrade_version(data):
    """Files from an older version will be run through this function.

    History:
    2.0: Base script
    2.0.1: Add acceleration tracking
    2.0.1b: Rename acceleration to speed, change tracking method
    2.0.2: Experimenting with combined speed and position tracks
    """
    get_id = VERSION_HISTORY.index

    #Make sure version is in history, otherwise set to lowest version
    try:
        current_version_id = get_id(str(data['Version']))
    except ValueError:
        current_version_id = 0
    
    if current_version_id < get_id('2.0.1'):
        data['Acceleration'] = {}
    if current_version_id < get_id('2.0.1b'):
        try:
            del data['Acceleration']
        except KeyError:
            pass
        data['Speed'] = {}
    if current_version_id < get_id('2.0.2'):
        data['Combined'] = {}
    
    data['Version'] = VERSION
    return data
