"""This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""
#Fix tracking data if a certain keyboard 'hack' is done in Path of Exile
#May also apply to other games, but will be a rare occurance

from __future__ import division

from ..files import LoadData, save_data
from ..image import RenderImage
from ..utils.compatibility import Message, range, input
from ..utils.input import yes_or_no
from ..utils.maths import round_int


def fix_poe_mine_build(profile_name, numpad_key):
    try:
        _num = 'NUM{}'.format(int(numpad_key))
    except ValueError:
        return False
    data = LoadData(profile_name, _reset_sessions=False)
    
    #Make sure record exists, quick delete if issue is obvious (0 press >0 held)
    try:
        if not data['Keys']['All']['Pressed'][_num]:
            raise KeyError
            
    except KeyError:
        try: 
            del data['Keys']['All']['Held'][_num]
        except KeyError:
            pass
            
    else:
        #Count the other numpad items
        total = {'pressed': 0, 'held': 0, 'count': 0}
        for i in range(1, 10):
            if i == numpad_key:
                 continue

            num = 'NUM{}'.format(i)
            try:
                 total['pressed'] += data['Keys']['All']['Pressed'][num]
                 total['held'] += data['Keys']['All']['Held'][num]
            except KeyError:
                pass
            else:
                total['count'] += 1

        #Get the average time the numpad is pressed for
        try:
            average_press_time = total['held'] / total['pressed']
        except ZeroDivisionError:
            average_press_time = 0
            Message('Unable to get an average as no other keypad data exists.')
            if not yes_or_no('Do you want to delete the numpad key instead?'):
                return False

        #Assign to numpad key
        new_held_time = round_int(data['Keys']['All']['Pressed'][_num] * average_press_time)
        data['Keys']['All']['Held'][_num] = new_held_time

    return save_data(profile_name, data)


Message('This is a fix for the numlock mine trick in Path of Exile.')
Message('The trick fools the computer into thinking the key is held down, but it doesn\'t release when the game is quit.')
Message('This fix replaces the \'held down\' time of the key with an average from the other numpad keys.')
Message('The issue is now fixed for other profiles, as the held down keys will be ignored after a profile switch.')
profile_name = input('Type the name of the profile to fix: ')
numpad_key = input('Type which numpad key is being used for mines: ')
Message('Please wait while the fix is completed...')
if fix_poe_mine_build(profile_name, numpad_key):
    Message('Finished updating profile.')
else:
    Message('Failed to update profile.')