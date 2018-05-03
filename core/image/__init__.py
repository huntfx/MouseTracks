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
from core.image.main import RenderImage
from core.input import value_select, yes_or_no
from core.files import get_data_files, get_metadata, format_name, LoadData
from core.language import STRINGS
from core.maths import round_up
from core.messages import date_format, ticks_to_seconds, list_to_str
from core.os import open_folder


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

    sort_options = ['Track Length', 'Session Count', 'Creation Time', 'Last Modified', 'File Version']
    sort_value = sort_options[3]
    reverse = False
    loop = 0
    while True:
        loop += 1
        offset = (page - 1) * limit
        '''
        Message('Select a profile by typing its name or the matching ID.')
        Message('Files are being sorted by "{} - {}".'.format(sort_value.lower(), 'ascending' if reverse else 'descending'))
        Message('Type "sort <ID>" to change or reverse the sorting method. Possible options are Track Length (1), Session Count (2), Creation Time (3), Last Modified (4) and File Version (5).')
        Message()
        '''
        Message(STRINGS['GenerationInput']['SelectProfile'])
        Message(STRINGS['GenerationInput']['PageSort'].format_custom(
                SORT_TYPE=sort_value.lower(), ORDER='ascending' if reverse else 'descending'))
        _sort_options = list_to_str(['{} ({})'.format(value, i+1) for i, value in enumerate(sort_options)])
        Message(STRINGS['GenerationInput']['PageSortSelect'].format_custom(
                SORT=STRINGS['Words']['Sort'], SORT_OPTIONS=_sort_options))
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
        Message(STRINGS['GenerationInput']['PageNumber'].format_custom(CURRENT_PAGE=page, 
                                                                       TOTAL_PAGES=total_pages, 
                                                                       PAGE=STRINGS['Words']['Page']))
        Message()

        #Ask the user for input, or automatically choose input for testing
        user_input = input(STRINGS['Misc']['UserChoice'] + ' ')

        try:
            profile_id = int(user_input)

        #Input is not an ID
        except ValueError:

            #Onput is requesting sorting
            if user_input.lower().startswith('{} '.format(STRINGS['Words']['Sort'])):
                option = None
                try:
                    sort_id = int(user_input[len(STRINGS['Words']['Sort']):]) - 1
                    print sort_id
                    if not 0 <= sort_id <= 4:
                        raise ValueError
                
                #Attempt to read if the option was manually typed out
                except ValueError:
                    lc_option = user_input[len(STRINGS['Words']['Sort'])+1:].lower()
                    for uc_option in sort_options:
                        if uc_option.lower() == lc_option:
                            option = uc_option
                            break
                    else:
                        #Message('Error: Invalid sorting ID. Must be between 1-5.')
                        try:
                            Message(STRINGS['GenerationInput']['PageSortInvalidID'].format_custom(
                                    CURRENT_SORT=sort_value, NEW_SORT=sort_id+1, SORT_MIN=1, SORT_MAX=5))
                        except UnboundLocalError:
                            Message(STRINGS['GenerationInput']['PageSortInvalidType'].format_custom(
                                    CURRENT_SORT=sort_value, NEW_SORT=lc_option, SORT_OPTIONS=_sort_options))
                #If sort by itself was typed, just reverse
                except IndexError:
                    reverse = not reverse

                #Get the ID
                else:
                    option = sort_options[sort_id]

                #Either reverse or change the sorting option
                if option is not None:
                    if option == sort_value:
                        reverse = not reverse
                        Message(STRINGS['GenerationInput']['PageSortReverse'])
                    else:
                        sort_value = option
                        Message(STRINGS['GenerationInput']['PageSortNew'].format_custom(SORT_TYPE=sort_value))

            #Switch pages
            elif user_input.lower().startswith('{} '.format(STRINGS['Words']['Page'])):
                _page = user_input[len(STRINGS['Words']['Page'])+1:]
                try:
                    page = int(_page)
                    if page < 1:
                        page = 1
                        raise ValueError
                    elif page > total_pages:
                        page = total_pages
                        raise ValueError
                
                except ValueError:
                    Message(STRINGS['GenerationInput']['PageNumberInvalid'].format_custom(
                            CURRENT_PAGE=page, PAGE=_page, PAGE_MIN=1, PAGE_MAX=total_pages))

            #Input is directly typing profile name
            else:
                if get_metadata(user_input) is None:
                    Message(STRINGS['GenerationInput']['ProfileEmpty'].format_custom(PROFILE=user_input))
                else:
                    profile = user_input
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
                Message(STRINGS['GenerationInput']['ProfileIndexError'].format_custom(
                        NEW_INDEX=profile_index, INDEX_MIN=1, INDEX_MAX=profile_index_max))
        Message()

    return profile


def check_running_status(profile):
    """Check if profile is running.
    Returns False if profile hasn't yet saved to allow for an easy quit.
    """
    if profile not in RunningApplications().all_loaded_apps():
        return True

    Message(STRINGS['GenerationInput']['ProfileRunning'].format_custom(PROFILE=profile))
    
    #Not saved yet
    metadata = get_metadata(profile)
    if metadata is None:
        Message(STRINGS['GenerationInput']['ProfileSaveNew'].format_custom(PROFILE=profile))
        Message(STRINGS['GenerationInput']['SaveFrequency'].format_custom(TIME=ticks_to_seconds(CONFIG['Save']['Frequency'])))
        return False
    
    #Calculate when the next save should be
    else:
        last_save_time = time.time() - float(metadata['modified'])
        last_save = ticks_to_seconds(last_save_time, allow_decimals=False)

        if last_save_time < CONFIG['Save']['Frequency']:
            next_save_time = CONFIG['Save']['Frequency'] - last_save_time
            next_save = ticks_to_seconds(next_save_time, allow_decimals=False, output_length=2)
            Message(STRINGS['GenerationInput']['ProfileSaveNext'].format_custom(PROFILE=profile,
                    PREVIOUS_SAVE=last_save, NEXT_SAVE=next_save))
        else:
            next_save_time = last_save_time - CONFIG['Save']['Frequency']
            next_save = ticks_to_seconds(next_save_time, allow_decimals=False, output_length=1)
            Message(STRINGS['GenerationInput']['ProfileSaveDue'].format_custom(PROFILE=profile,
                    PREVIOUS_SAVE=last_save, NEXT_SAVE=next_save))
        Message()
        return True


def _user_generate():
    profile = select_profile_from_list()

    if not check_running_status(profile):
        Message(STRINGS['Misc']['ProgramExit'])
        return

    Message(STRINGS['Misc']['ProfileLoad'].format_custom(PROFILE=profile))
    render = RenderImage(profile)

    #Ask for type of render
    render_types = [
        ['tracks', True, STRINGS['RenderTypes']['Tracks'], []],
        ['click heatmap', True, STRINGS['RenderTypes']['Clicks'], []],
        ['keyboard heatmap', True, STRINGS['RenderTypes']['Keyboard'], []],
        ['acceleration', False, STRINGS['RenderTypes']['Speed'], []],
        ['brush strokes', False, STRINGS['RenderTypes']['Strokes'], []]
    ]

    #Set keyboard default to False if not tracked
    kph = round(render.keys_per_hour(), 2)
    if kph < 10:
        render_types[2][1] = False
        render_types[2][2] += ' ' + STRINGS['GenerationInput']['KeyboardNoUse'].format_custom(KEYS_PER_HOUR=kph)

    Message()
    Message(STRINGS['GenerationInput']['GenerateChoice'])
    if not any(select_options(render_types, multiple_choice=True)):
        if yes_or_no(STRINGS['GenerationInput']['NoSelection']):
            return True
        return False

    #Generate tracks
    if render_types[0][1]:
        Message(STRINGS['GenerationInput']['OptionsForRender'].format_custom(RENDER_TYPE=render_types[0][0]))

        #Select colour map
        try:
            colour_map_gen = calculate_colour_map(CONFIG['GenerateTracks']['ColourProfile'])
        except ValueError:
            Message(STRINGS['GenerationInput']['ColourNotSet'])
            map_options = [[colours, False, colours] for colours in sorted(get_map_matches(tracks=True))]
            
            while not render_types[0][3]:
                colour_maps = multi_select(map_options)
                for colour_map in colour_maps:
                    try:
                        calculate_colour_map(colour_map)
                    except ValueError as e:
                        Message('Warning: Failed to convert {} into a colour map. Reason: {}'.format(colour_map), e)
                    else:
                        render_types[0][3].append(colour_map)
                if not render_types[0][3]:
                    Message('Error: No valid colour maps in selection. Please make another choice or leave empty for a random choice.')
        else:
            render_types[0][3].append(CONFIG['GenerateStrokes']['ColourProfile'])
                
    
    #Generate click heatmap
    if render_types[1][1]:
        Message('Options for {}...'.format(render_types[1][0]))

        #Select mouse button
        mb_options = [
            ['_MouseButtonLeft', CONFIG['GenerateHeatmap']['_MouseButtonLeft'], STRINGS['Mouse']['MouseButtonLeft']],
            ['_MouseButtonMiddle', CONFIG['GenerateHeatmap']['_MouseButtonMiddle'], STRINGS['Mouse']['MouseButtonMiddle']],
            ['_MouseButtonRight', CONFIG['GenerateHeatmap']['_MouseButtonRight'], STRINGS['Mouse']['MouseButtonRight']]
        ]
        Message('Which mouse buttons should be included in the heatmap?.')
        if not any(select_options(mb_options, multiple_choice=True)):
            Message('Warning: No mouse buttons selected, disabling heatmap.')
            render_types[2][1] = False
        else:
            for mb_id, value, _ in mb_options:
                CONFIG['GenerateHeatmap'][mb_id] = value
        
        #Select colour map
        try:
            colour_map_gen = calculate_colour_map(CONFIG['GenerateHeatmap']['ColourProfile'])
        except ValueError:
            Message(STRINGS['GenerationInput']['ColourNotSet'])
            map_options = [[colours, False, colours] for colours in sorted(get_map_matches(clicks=True))]
            
            while not render_types[1][3]:
                colour_maps = multi_select(map_options)
                for colour_map in colour_maps:
                    try:
                        calculate_colour_map(colour_map)
                    except ValueError as e:
                        Message('Warning: Failed to convert {} into a colour map. Reason: {}'.format(colour_map), e)
                    else:
                        render_types[1][3].append(colour_map)
                if not render_types[1][3]:
                    Message('Error: No valid colour maps in selection. Please make another choice or leave empty for a random choice.')
        else:
            render_types[1][3].append(CONFIG['GenerateStrokes']['ColourProfile'])

                    
    #Generate keyboard
    if render_types[2][1]:
        Message('Options for {}...'.format(render_types[2][0]))

        #Get colour map
        try:
            colour_map_gen = calculate_colour_map(CONFIG['GenerateKeyboard']['ColourProfile'])
        except ValueError:
            Message(STRINGS['GenerationInput']['ColourNotSet'])
            map_options = [[colours, False, colours] for colours in sorted(get_map_matches(keyboard=True, linear=CONFIG['GenerateKeyboard']['LinearMapping']))]

            while not render_types[2][3]:
                colour_maps = multi_select(map_options)
                for colour_map in colour_maps:
                    try:
                        calculate_colour_map(colour_map)
                    except ValueError as e:
                        Message('Warning: Failed to convert {} into a colour map. Reason: {}'.format(colour_map), e)
                    else:
                        render_types[2][3].append(colour_map)
                if not render_types[2][3]:
                    Message('Error: No valid colour maps in selection. Please make another choice or leave empty for a random choice.')
        else:
            render_types[2][3].append(CONFIG['GenerateStrokes']['ColourProfile'])

    #Generate acceleration
    if render_types[3][1]:
        Message('Options for {}...'.format(render_types[3][0]))

        #Select colour map
        try:
            colour_map_gen = calculate_colour_map(CONFIG['GenerateSpeed']['ColourProfile'])
        except ValueError:
            Message(STRINGS['GenerationInput']['ColourNotSet'])
            map_options = [[colours, False, colours] for colours in sorted(get_map_matches(tracks=True))]

            while not render_types[3][3]:
                colour_maps = multi_select(map_options)
                for colour_map in colour_maps:
                    try:
                        calculate_colour_map(colour_map)
                    except ValueError as e:
                        Message('Warning: Failed to convert {} into a colour map. Reason: {}'.format(colour_map), e)
                    else:
                        render_types[3][3].append(colour_map)
                if not render_types[3][3]:
                    Message('Error: No valid colour maps in selection. Please make another choice or leave empty for a random choice.')
        else:
            render_types[3][3].append(CONFIG['GenerateStrokes']['ColourProfile'])


    #Generate brush strokes
    if render_types[4][1]:
        Message('Options for {}...'.format(render_types[4][0]))

        #Select colour map
        try:
            colour_map_gen = calculate_colour_map(CONFIG['GenerateStrokes']['ColourProfile'])
        except ValueError:
            Message(STRINGS['GenerationInput']['ColourNotSet'])
            map_options = [[colours, False, colours] for colours in sorted(get_map_matches(tracks=True))]

            while not render_types[4][3]:
                colour_maps = multi_select(map_options)
                for colour_map in colour_maps:
                    try:
                        calculate_colour_map(colour_map)
                    except ValueError as e:
                        Message('Warning: Failed to convert {} into a colour map. Reason: {}'.format(colour_map), e)
                    else:
                        render_types[4][3].append(colour_map)
                if not render_types[4][3]:
                    Message('Error: No valid colour maps in selection. Please make another choice or leave empty for a random choice.')
        else:
            render_types[4][3].append(CONFIG['GenerateStrokes']['ColourProfile'])


    #Calculate session length
    last_session_start = render.data['Ticks']['Session']['Total']
    last_session_end = render.data['Ticks']['Total']
    all_time = ticks_to_seconds(last_session_end, UPDATES_PER_SECOND)
    last_session_time = ticks_to_seconds(last_session_end - last_session_start, tick_rate=UPDATES_PER_SECOND, allow_decimals=False)
    if not last_session_time or last_session_time == all_time:
        last_session_time = None

    #Ask if session or all data should be used
    session = False
    if last_session_time is not None:
        session_options = [
            [False, True, STRINGS['GenerationInput']['SessionAll'].format_custom(TIME=all_time)],
            [True, False,  STRINGS['GenerationInput']['SessionLatest'].format_custom(TIME=last_session_time)]
        ]
        Message(STRINGS['GenerationInput']['SessionSelect'])
        while True:
            session = select_options(session_options, multiple_choice=False, update=False)
            if session is not None:
                break
    
    #Render the images
    if render_types[0][1]:
        for colour_map in render_types[0][3]:
            CONFIG['GenerateTracks']['ColourProfile'] = colour_map
            render.tracks(session)
            Message()
    if render_types[1][1]:
        for colour_map in render_types[1][3]:
            CONFIG['GenerateHeatmap']['ColourProfile'] = colour_map
            render.clicks(session)
            Message()
    if render_types[2][1]:
        for colour_map in render_types[2][3]:
            CONFIG['GenerateKeyboard']['ColourProfile'] = colour_map
            render.keyboard(session)
            Message()
    if render_types[3][1]:
        for colour_map in render_types[2][3]:
            CONFIG['GenerateSpeed']['ColourProfile'] = colour_map
            render.speed(session)
            Message()
    if render_types[4][1]:
        for colour_map in render_types[2][3]:
            CONFIG['GenerateStrokes']['ColourProfile'] = colour_map
            render.strokes(session)
            Message()
        
    #Open folder
    if CONFIG['GenerateImages']['OpenOnFinish']:
        Message(STRINGS['Misc']['OpenImageFolder'])
        open_folder(render.name.generate())
    
    return False


def user_generate():
    "Wrapper for _user_generate to allow for looping back to start."
    while True:
        CONFIG.reload()
        auto_restart = _user_generate()
        Message()
        if not auto_restart and not yes_or_no('Finished image generation. Would you like to run it again?'):
            break


def select_options(options, multiple_choice=True, update=None, auto_choose_on_fail=False, _show_choice_only=None, _selection=None):
    """Ask for either single or multiple choice input.

    Parameters:
        options (list/tuple): Information on the selection.
            options[0] = return value (str)
            options[1] = default (bool)
            options[2] = name
            options[3:] = anything

        multiple_choice (bool): If multiple answers can be chosen.
            Default: True

        update (bool/None): If the options list should be modified in place.
            Disable if the default values need to be used again.
            By default it is set to match the multiple_choice option.
            Default: None

        auto_choose_on_fail (bool): If a random choice should be used when nothing is selected.
            If disabled without multiple_choice, None will be returned and an error will be printed.
            Default: False
        
        _show_choice_only (bool/None): If the choice should be shown, or input disabled.
            Only should be used if overriding the function.
            If set to True, a list of options will be shown with no input.
            If set to False, an input will be requested without options.
            If set to "input_override", it acts as True but asks for the input and instantly returns it.

        _selection (str/None): Pre-chosen selection to override the input.

    Return Values:
        If multiple_choice is True: 
            Return list of booleans for each option value

        If multiple_choice is False:
            If one option chosen:
                Return option[0] (the return value) of chosen option
            If more than one option chosen:
                Return None
            If auto_choose_on_fail is False and no selection given: 
                Return None

        If _show_choice_only is True:
            Return None

        If _show_choice_only is "input_override":
            Return user input

    >>> options = [
    ...     ['option_1', False, 'Option 1'],
    ...     ['option_2', False, 'Option 2'],
    ...     ['option_3', False, 'Option 3']
    ... ]
    >>> select_options(options, multiple_choice=False, auto_choose_on_fail=False) <press 1>
    option_1
    >>> select_options(options, multiple_choice=False, auto_choose_on_fail=False) <press 1 2>
    None
    >>> select_options(options, multiple_choice=False, auto_choose_on_fail=False) <no choice>
    None
    >>> select_options(options, multiple_choice=False, auto_choose_on_fail=True) <no choice>
    option_2
    >>> select_options(options, multiple_choice=True, auto_choose_on_fail=False) <press 1>
    [True, False, False]
    >>> select_options(options, multiple_choice=True, auto_choose_on_fail=False) <press 1 2>
    [True, True, False]
    >>> select_options(options, multiple_choice=True, auto_choose_on_fail=False) <no choice>
    [False, False, False]
    >>> select_options(options, multiple_choice=True, auto_choose_on_fail=True) <no choice>
    [True, False, True]
    """
    if update is None:
        update = multiple_choice

    #List possible options
    if multiple_choice and _show_choice_only is None:
        Message(STRINGS['GenerationInput']['SeparateOptions'].format_custom(VALUE=', '.join(i[2] for i in options if i[1]), 
                ID=', '.join(str(i+1) for i, value in enumerate(options) if value[1])))

    for i, values in enumerate(options):

        #Set name to return value if name doesn't exist
        if len(values) == 2:
            values.append(values[0])

        if _show_choice_only is None or _show_choice_only: 
            if multiple_choice or not values[1]:
                Message('{}: {}'.format(i+1, values[2]))
            else:
                Message('{}: {} [{}]'.format(i+1, values[2], STRINGS['Words']['Default']))
    
    #Handle override to show/hide choice
    if _show_choice_only and _show_choice_only != 'input_override':
        return None
    elif _show_choice_only is None or _show_choice_only:
        Message()
    
    if _selection is None:
        choice = input(STRINGS['Misc']['UserChoice'] + ' ')
    else:
        choice = _selection

    if _show_choice_only == 'input_override':
        return choice

    #Get choice results, and update options if needed
    result = value_select(choice, [option[1] for option in options], start=1, revert_to_default=not auto_choose_on_fail)
    if update:
        for i, value in enumerate(result):
            options[i][1] = value
    
    #Return different output depending on if multiple choices were allowed
    joined = [options[i][0] for i, value in enumerate(result) if value]
    if any(result):
        Message('{} {} chosen.'.format(list_to_str(options[i][2] for i, value in enumerate(result) if value), 'was' if len(joined) == 1 else 'have been'))
    
    #Automatically choose if no selection given
    elif auto_choose_on_fail and not choice:
        if multiple_choice:
            num_results = len(result) - 1
            while not any(result):
                result = [not random.randint(0, num_results) for _ in result]
            Message('{} {} chosen at random.'.format(list_to_str(options[i][2] for i, value in enumerate(result) if value), 'was' if sum(result) == 1 else 'have been'))
        else:
            result = random.choice(options)[0]
            Message('{} was chosen at random.\n'.format(result))
            return result
    
    #End if multiple choice
    if multiple_choice:
        Message()
        return result

    #Check too many options haven't been chosen
    elif joined:
        if len(joined) > 1:
            Message('Error: Only one option can be chosen.\n')
            return None
        Message()
        return joined[0]
    
    #End if random choice was chosen
    else:
        if not auto_choose_on_fail:
            Message('Error: Invalid choice.\n')
            return None
        else:
            Message('{} was chosen.\n'.format(choice))
            return choice


def multi_select(options, auto=False):
    """Override of the select_options function to allow both text and integer input for multiple choice."""

    if not auto:

        #Display the options
        choice = select_options(options, multiple_choice=True, _show_choice_only='input_override')

        #Read the integer selections
        int_choice = value_select(choice, [option[1] for option in options], start=1, revert_to_default=True)
        for i, value in enumerate(int_choice):
            if value:
                choice = choice.replace(str(i+1), '')
        multiple_choice = set(options[i][0] for i, value in enumerate(int_choice) if value)

        #Parse the text input
        multiple_choice.update(i.strip() for i in choice.replace(' ', ',').split(','))
        try:
            multiple_choice.remove('')
        except KeyError:
            pass

    #Get random selection
    if auto or not multiple_choice:
        random_choice = select_options(options, multiple_choice=True, auto_choose_on_fail=True, _selection='', _show_choice_only=False)
        multiple_choice = set(options[i][0] for i, value in enumerate(random_choice) if value)
    
    return multiple_choice


if __name__ == '__main__':
    Message('Note: These questions are temporary until a user inferface is done.')
    user_generate()