"""
This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""

from __future__ import division

import os
import random
import sys
import time

from core.applications import RunningApplications, AppList
from core.compatibility import input, Message
from core.constants import DEFAULT_NAME, UPDATES_PER_SECOND
from core.config import CONFIG
from core.image.colours import get_map_matches, calculate_colour_map
from core.input import value_select, yes_or_no
from core.files import get_data_files, get_metadata, format_name, LoadData
from core.language import Language
from core.maths import round_up
from core.messages import date_format, ticks_to_seconds, list_to_str
from core.os import open_folder


STRINGS = Language().get_strings()

SORT_OPTIONS = {
    #Name: metadata name, default, type, (function, args, kwargs)
    #TODO: filesize
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


def select_profile_from_list(data_files=None, page=1, limit=20, metadata_offset=40):
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
        Message('Select a profile by typing its name or the matching ID.')
        Message('Files are being sorted by "{} - {}".'.format(sort_value.lower(), 'ascending' if reverse else 'descending'))
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
        user_input = input('Type your choice here: ')

        try:
            profile_id = int(user_input)

        #Input is not an ID
        except ValueError:

            #Onput is requesting sorting
            if user_input.startswith('sort'):
                option = None
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
                        Message('Error: Invalid sorting ID. Must be between 1-5.')

                #If sort by itself was typed, just reverse
                except IndexError:
                    reverse = not reverse

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
                    page = int(user_input[5:])
                    if page < 1:
                        page = 1
                        raise ValueError
                    elif page > total_pages:
                        page = total_pages
                        raise ValueError
                
                except ValueError:
                    Message('Error: Invalid page number.')

            #Input is directly typing profile name
            else:
                profile = user_input
                if get_metadata(profile) is None:
                    Message('Error: Profile doesn\'t exist.')
                else:
                    break
        
        #Get the profile matching the ID
        else:
            profile_index = profile_id
            if 1 <= profile_index <= profile_index_max:
                try:
                    profile = program_names[sorted_list[profile_index-1]]
                except KeyError:
                    profile = sorted_list[profile_index-1]
                break
            else:
                Message('Error: Invalid profile index.')
        Message()

    return profile


def check_running_status(profile):
    """Check if profile is running.
    Returns False if profile hasn't yet saved to allow for an easy quit.
    """
    if profile not in RunningApplications().all_loaded_apps():
        return True

    Message(STRINGS['string']['image']['profile']['running'])
    
    #Not saved yet
    metadata = get_metadata(profile)
    if metadata is None:
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
        Message()
        return True


def _user_generate():
    profile = select_profile_from_list()

    if not check_running_status(profile):
        Message(STRINGS['string']['exit'])
        return

    #Load functions
    Message(STRINGS['string']['import'])
    from core.image.main import RenderImage

    Message(STRINGS['string']['profile']['load'].format(P=profile))
    try:
        render = RenderImage(profile)
    except ValueError:
        Message('Error: Selected profile is empty or doesn\'t exist. (this message shouldn\'t appear')
        return

    #Ask for type of render
    render_types = [
        ['tracks', True, STRINGS['string']['image']['name']['track']],
        ['click heatmap', True, STRINGS['string']['image']['name']['click']],
        ['keyboard heatmap', True, STRINGS['string']['image']['name']['keyboard']],
        ['acceleration', False, STRINGS['string']['image']['name']['speed']],
        ['brush strokes', False, STRINGS['string']['image']['name']['stroke']]
    ]

    #Edit keyboard if not tracked
    kph = round(render.keys_per_hour(), 2)
    if kph < 10:
        render_types[3][1] = False
        render_types[3][2] += ' ({})'.format(STRINGS['string']['image']['name']['empty']['keyboard']).format(C=kph)

    Message()
    Message(STRINGS['string']['image']['option']['generate'])
    if not any(select_options(render_types, allow_multiple=True)):
        if yes_or_no('Error: Nothing was chosen, would you like to restart?'):
            return True
        return False

    #Generate tracks
    if render_types[0][1]:
        Message('Options for {}...'.format(render_types[0][0]))

        #Select colour map
        try:
            colour_map_gen = calculate_colour_map(CONFIG['GenerateTracks']['ColourProfile'])
        except ValueError:
            Message(STRINGS['string']['image']['option']['colour']['notset'])
            map_options = [[colours, False, colours] for colours in sorted(get_map_matches(tracks=True))]

            while True:
                colour_map = select_options(map_options, allow_multiple=False, allow_fail=False)
                if colour_map is None:
                    continue
                try:
                    colour_map_gen = calculate_colour_map(colour_map)
                    CONFIG['GenerateTracks']['ColourProfile'] = colour_map
                    break
                except ValueError:
                    Message('Error: Failed to turn {} into a colour map. Please choose another:'.format(colour_map))
    
    #Generate click heatmap
    if render_types[1][1]:
        Message('Options for {}...'.format(render_types[1][0]))

        #Select mouse button
        mb_options = [
            ['_MouseButtonLeft', CONFIG['GenerateHeatmap']['_MouseButtonLeft'], STRINGS['word']['mousebutton']['left']],
            ['_MouseButtonMiddle', CONFIG['GenerateHeatmap']['_MouseButtonMiddle'], STRINGS['word']['mousebutton']['middle']],
            ['_MouseButtonRight', CONFIG['GenerateHeatmap']['_MouseButtonRight'], STRINGS['word']['mousebutton']['right']]
        ]
        Message('Which mouse buttons should be included in the heatmap?.')
        if not any(select_options(mb_options, allow_multiple=True)):
            Message('Warning: No mouse buttons selected, disabling heatmap.')
            render_types[2][1] = False
        else:
            for mb_id, value, _ in mb_options:
                CONFIG['GenerateHeatmap'][mb_id] = value
        
        #Select colour map
        colour_map = CONFIG['GenerateHeatmap']['ColourProfile']
        try:
            colour_map_gen = calculate_colour_map(colour_map)
        except ValueError:
            Message(STRINGS['string']['image']['option']['colour']['notset'])
            map_options = [[colours, False, colours] for colours in sorted(get_map_matches(clicks=True))]

            while True:
                colour_map = select_options(map_options, allow_multiple=False, allow_fail=False)
                if colour_map is None:
                    continue
                try:
                    colour_map_gen = calculate_colour_map(colour_map)
                    CONFIG['GenerateHeatmap']['ColourProfile'] = colour_map
                    break
                except ValueError:
                    Message('Error: Failed to turn {} into a colour map. Please choose another:'.format(colour_map))
                    
    #Generate keyboard
    if render_types[2][1]:
        Message('Options for {}...'.format(render_types[2][0]))

        #Get colour map
        colour_map = CONFIG['GenerateKeyboard']['ColourProfile']
        try:
            colour_map_gen = calculate_colour_map(colour_map)
        except ValueError:
            Message(STRINGS['string']['image']['option']['colour']['notset'])
            map_options = [[colours, False, colours] for colours in sorted(get_map_matches(keyboard=True, linear=CONFIG['GenerateKeyboard']['LinearMapping']))]

            while True:
                colour_map = select_options(map_options, allow_multiple=False, allow_fail=False)
                if colour_map is None:
                    continue
                try:
                    colour_map_gen = calculate_colour_map(colour_map)
                    CONFIG['GenerateKeyboard']['ColourProfile'] = colour_map
                    break
                except ValueError:
                    Message('Error: Failed to turn {} into a colour map. Please choose another:'.format(colour_map))

    #Generate acceleration
    if render_types[3][1]:
        Message('Options for {}...'.format(render_types[3][0]))

        #Select colour map
        colour_map = CONFIG['GenerateSpeed']['ColourProfile']
        try:
            colour_map_gen = calculate_colour_map(colour_map)
        except ValueError:
            Message(STRINGS['string']['image']['option']['colour']['notset'])
            map_options = [[colours, False, colours] for colours in sorted(get_map_matches(tracks=True))]

            while True:
                colour_map = select_options(map_options, allow_multiple=False, allow_fail=False)
                if colour_map is None:
                    continue
                try:
                    colour_map_gen = calculate_colour_map(colour_map)
                    CONFIG['GenerateSpeed']['ColourProfile'] = colour_map
                    break
                except ValueError:
                    Message('Error: Failed to turn {} into a colour map. Please choose another:'.format(colour_map))

    #Generate brush strokes
    if render_types[4][1]:
        Message('Options for {}...'.format(render_types[4][0]))

        #Select colour map
        colour_map = CONFIG['GenerateStrokes']['ColourProfile']
        try:
            colour_map_gen = calculate_colour_map(colour_map)
        except ValueError:
            Message(STRINGS['string']['image']['option']['colour']['notset'])
            map_options = [[colours, False, colours] for colours in sorted(get_map_matches(tracks=True))]

            while True:
                colour_map = select_options(map_options, allow_multiple=False, allow_fail=False)
                if colour_map is None:
                    continue
                try:
                    colour_map_gen = calculate_colour_map(colour_map)
                    CONFIG['GenerateStrokes']['ColourProfile'] = colour_map
                    break
                except ValueError:
                    Message('Error: Failed to turn {} into a colour map. Please choose another:'.format(colour_map))

    #Calculate session length
    last_session_start = render.data['Ticks']['Session']['Total']
    last_session_end = render.data['Ticks']['Total']
    all_time = ticks_to_seconds(last_session_end, UPDATES_PER_SECOND)
    last_session_time = ticks_to_seconds(last_session_end - last_session_start, tick_rate=UPDATES_PER_SECOND, allow_decimals=False)
    if not last_session_time or last_session_time == all_time:
        last_session_time = None

    #Ask if session or all data should be used
    session_options = [
        [False, True, STRINGS['string']['image']['option']['session']['all'].format(T=all_time)],
        [True, False, STRINGS['string']['image']['option']['session']['last'].format(T=last_session_time)]
    ]
    Message(STRINGS['string']['image']['option']['session']['select'])
    while True:
        session = select_options(session_options, allow_multiple=False, update=False)
        if session is not None:
            break
    
    #Render the images
    if render_types[0][1]:
        render.tracks(session)
        Message()
    if render_types[1][1]:
        render.clicks(session)
        Message()
    if render_types[2][1]:
        render.keyboard(session)
        Message()
    if render_types[3][1]:
        render.speed(session)
        Message()
    if render_types[4][1]:
        render.strokes(session)
        Message()
        
    #Open folder
    if CONFIG['GenerateImages']['OpenOnFinish']:
        Message(STRINGS['string']['image']['option']['open'])
        open_folder(render.name.generate())
    
    return False


def user_generate():
    "Wrapper for _user_generate to allow for looping back to start."
    while True:
        auto_restart = _user_generate()
        Message()
        if not auto_restart and not yes_or_no('Finished image generation. Would you like to run it again?'):
            break


def select_options(options, allow_multiple=True, update=None, allow_fail=True):
    """Ask for choices (either multiple or single).
    The options must be in the format: [Return Value, True/False, Name]

    The options can be automatically updated but the default settings will be lost.

    "show_fail" is used when you want the output, like if you were choosing a string.
    """
    if update is None:
        update = allow_multiple

    #List possible options
    if allow_multiple:
        Message(STRINGS['string']['image']['option']['select'].format(V=', '.join(i[2] for i in options if i[1]), 
                                                                    ID=', '.join(str(i+1) for i, value in enumerate(options) if value[1])))
    for i, values in enumerate(options):
        if allow_multiple or not values[1]:
            Message('{}: {}'.format(i+1, values[2]))
        else:
            Message('{}: {} [{}]'.format(i+1, values[2], STRINGS['word']['default']))
    Message()
    
    choice = input('Type your choice here: ')

    #Get choice results, and update options if needed
    result = value_select(choice, [option[1] for option in options], start=1, revert_to_default=allow_fail)
    if update:
        for i, value in enumerate(result):
            options[i][1] = value
    
    #Return different output depending on if multiple choices were allowed
    joined = [options[i][0] for i, value in enumerate(result) if value]
    if any(result):
        Message('{} {} chosen.'.format(list_to_str(options[i][2] for i, value in enumerate(result) if value), 'was' if len(joined) == 1 else 'have been'))
    
    #Choose at random if single choice and failing is not allowed
    elif not allow_fail and not allow_multiple and not choice:
        result = random.choice(options)[0]
        Message('{} was chosen at random.\n'.format(result))
        return result

    if allow_multiple:
        Message()
        return result

    elif len(joined) > 1:
        Message('Error: Only one option can be chosen.\n')
        return None

    try:
        Message('{} was chosen.\n'.format(joined[0]))
        return joined[0]

    except IndexError:
        if allow_fail:
            Message('Error: Invalid choice.\n')
            return None
        else:
            Message('{} was chosen.\n'.format(choice))
            return choice


if __name__ == '__main__':
    Message('Note: These questions are temporary until a user inferface is done.')
    user_generate()