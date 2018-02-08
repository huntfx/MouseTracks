"""
This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""

from __future__ import division

import os
import sys
import time

from core.applications import RunningApplications, AppList
from core.compatibility import input, Message
from core.constants import DEFAULT_NAME, UPDATES_PER_SECOND
from core.config import CONFIG
from core.files import get_data_files, get_metadata, format_name, LoadData
from core.image import user_generate_image
from core.language import Language
from core.maths import round_up
from core.messages import date_format, ticks_to_seconds

#from core.image.colours import get_map_matches
#from core.image.main import RenderImage
#from core.input import value_select, yes_or_no


STRINGS = Language().get_strings()

SORT_OPTIONS = {
    'Track Length': ('time', 0, int, None),
    'Session Count': ('sessions', 0, int, None),
    'Creation Time': ('created', 0, float, (date_format, (), {'include_time': False})),
    'Last Modified': ('modified', 0, float, (date_format, (), {'include_time': False})),
    'File Version': ('file', 0, int, None)
}


def _sort_data_list(data_files, option, descending=True):
    """Sort the list of data files by metadata."""
    option_name, option_default, option_type, _ = SORT_OPTIONS[option]
    new_list = sorted(data_files, key=lambda k: option_type(data_files[k].get(option_name, option_default)))
    if descending:
        new_list = new_list[::-1]
    return new_list


def select_profile_from_list(data_files=None, page=1, limit=10, metadata_offset=40, _debug=True):
    """Ask the user to choose a profile."""

    #Read list of files in data folder
    if data_files is None:
        data_files = get_data_files()
    profile_index_max = len(data_files)
    total_pages = round_up(profile_index_max / limit)

    #Build and sort list of all known program names
    program_names = {format_name(DEFAULT_NAME): DEFAULT_NAME}
    for program_name in AppList().names:
        program_names[format_name(program_name)] = program_name

    sort_value = 'Last Modified'
    reverse = False
    loop = 0
    while True:
        loop += 1
        offset = (page - 1) * limit
        Message('Files are being sorted by "{} - {}".'.format(sort_value.lower(), 'ascending' if reverse else 'descending'))
        Message('Select a profile by typing its name or the matching ID.')
        Message('Type "sort <ID>" to change or reverse the sorting method. Possible options are Track Length (1), Session Count (2), Creation Time (3), Last Modified (4) and File Version (5).')
        Message()
        sorted_list = _sort_data_list(data_files, sort_value, not reverse)
        option_name, _, option_type, option_func = SORT_OPTIONS[sort_value]
        for i, profile_name in enumerate(sorted_list[offset:offset+limit]):
            output = '{}: '.format(offset+i+1)

            #Get the full name of the profile
            try:
                output += program_names[profile_name]
            except KeyError:
                output += profile_name

            #Add information relating to current sorting selection
            try:
                value = option_type(data_files[profile_name][option_name])
            except KeyError:
                pass
            else:
                if option_func is not None:
                    value = option_func[0](value, *option_func[1], **option_func[2])
                output += ' ' * max(1, metadata_offset - len(output)) + '{}: {}'.format(sort_value, value)
            Message(output)
        Message(STRINGS['string']['image']['page']['current'].format(C=page, T=total_pages, P=STRINGS['word']['page']))
        Message()

        #Ask the user for input, or automatically choose input for testing
        if not _debug:
            user_input = input('Type your option here: ')
        else:
            if loop == 0:
                user_input = 'sort 1'
            elif loop == 1:
                user_input = 'page 2'
            elif loop == 2:
                user_input = 'sort track length'
            elif loop == 3:
                user_input = 'testing'
            elif loop == 4:
                user_input = '13'
            else:
                break
            Message('Type your option here: {}'.format(user_input))

        try:
            profile_id = int(user_input)

        #Input is not an ID
        except ValueError:

            #Onput is requesting sorting
            if user_input.startswith('sort '):
                options = ['Track Length', 'Session Count', 'Creation Time', 'Last Modified', 'File Version']
                try:
                    sort_id = int(user_input[5]) - 1
                    if not 0 <= sort_id <= 4:
                        raise ValueError
                
                #Attempt to read if the option was manually typed out
                except ValueError:
                    lc_option = user_input[5:].lower()
                    for uc_option in options:
                        if uc_option.lower() == lc_option:
                            option = uc_option
                            break
                    else:
                        option = None
                        Message('Error: Invalid sorting ID. Must be between 1-5.')
                
                #Get the ID
                else:
                    option = options[sort_id]

                #Either reverse or change the sorting option
                if option is not None:
                    if option == sort_value:
                        reverse = not reverse
                        Message('Reversed sorting.')
                    else:
                        sort_value = option
                        Message('List sorting changed to {}.'.format(sort_value))

            #Switch pages
            elif user_input.startswith('page '):
                try:
                    page = int(user_input[5])
                    if not 1 <= page <= total_pages:
                        raise ValueError
                
                except ValueError:
                    Message('Error: Invalid page number.')

            #Input is directly typing profile name
            else:
                profile = user_input
                data = LoadData(profile, _reset_sessions=False, _update_metadata=False)
                if not data['Ticks']['Total']:
                    Message('Error: Profile doesn\'t exist.')
                else:
                    break
        
        #Get the profile matching the ID
        else:
            profile_index = profile_id - 1
            if 1 <= profile_index < profile_index_max:
                try:
                    profile = program_names[sorted_list[profile_index]]
                except KeyError:
                    profile = sorted_list[profile_index]
                data = LoadData(profile, _reset_sessions=False, _update_metadata=False)
                break
            else:
                Message('Error: Invalid profile index.')
        Message()

    return profile, data


def check_running_status(profile):
    """Check if profile is running.
    Returns False if profile hasn't yet saved to allow for an easy quit.
    """
    if profile not in RunningApplications().all_loaded_apps():
        return True

    Message(STRINGS['string']['image']['profile']['running'])
    
    #Not saved yet
    metadata = get_metadata(profile)
    if metadata is None or True:
        Message(STRINGS['string']['image']['save']['wait'])
        Message(STRINGS['string']['image']['save']['frequency'].format(T=ticks_to_seconds(CONFIG['Save']['Frequency'])))
        return False
    
    #Calculate when the next save should be
    else:
        last_save_time = time.time() - float(metadata['modified'])
        last_save = ticks_to_seconds(last_save_time, allow_decimals=False)

        if last_save_time < CONFIG['Save']['Frequency']:
            next_save_time = CONFIG['Save']['Frequency'] - last_save_time
            next_save = ticks_to_seconds(next_save_time, allow_decimals=False, output_length=2)
            Message(STRINGS['string']['image']['save']['next'].format(T1=last_save, T2=next_save))
        else:
            next_save_time = last_save_time - CONFIG['Save']['Frequency']
            next_save = ticks_to_seconds(next_save_time, allow_decimals=False, output_length=1)
            Message(STRINGS['string']['image']['save']['overdue'].format(T1=last_save, T2=next_save))
        return True


def _user_generate_image():
    """Idea on how it should work."""
    #Show list of profiles

    #Loop until existing profile is chosen

    #Warn if profile is currently running

    #Do you want tracks/clicks/keyboard?

    #What colour (if not set in config)?
    colour_maps = parse_colour_file()['Maps']
    get_map_matches(colour_maps, tracks=True)
    get_map_matches(colour_maps, clicks=True)
    get_map_matches(colour_maps, keyboard=True) #Find if keyboard is linear colours

    #Just the session or all data?

    #Open folder