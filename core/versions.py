VERSION_HISTORY = [
    '2.0',
    '2.0.1',
    '2.0.1b',
    '2.0.2',
    '2.0.3'
]
VERSION = VERSION_HISTORY[-1]

def upgrade_version(data):
    """Files from an older version will be run through this function.

    History:
    2.0: Base script
    2.0.1: Add acceleration tracking
    2.0.1b: Rename acceleration to speed, change tracking method
    2.0.2: Experimenting with combined speed and position tracks
    2.0.3: Separate click maps, record both keys pressed and how long
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
        del data['Acceleration']
        data['Speed'] = {}
    if current_version_id < get_id('2.0.2'):
        data['Combined'] = {}
    if current_version_id < get_id('2.0.3'):
        data['Clicks'] = {}
        data['Keys'] = {'Pressed': {}, 'Held': {}}
        data['Ticks'] = {'Current': data['Count'],
                         'Total': data['Ticks'],
                         'Recorded': data['Count']}
        del data['Count']
    
    data['Version'] = VERSION
    return data
