from __future__ import division
import time
import sys

from core.constants import CONFIG, DEFAULT_NAME
from core.files import list_files, format_name, load_program
from core.functions import ticks_to_seconds, RunningPrograms, simple_bit_mask
from core.simple import round_up

if sys.version_info.major != 2:
    raw_input = input

def user_generate():
    CONFIG.save()
    print('Type profile to load, or type "list" to see them all:')
    profile = raw_input()

    if profile == 'list':

        #Read the data folder and format names
        all_files = sorted(list_files())
        if not all_files:
            print('Sorry, nothing was found in the data folder.')
            print('Press enter to exit.')
            raw_input()
            sys.exit()
        programs = {format_name(DEFAULT_NAME): DEFAULT_NAME}
        for program_name in RunningPrograms(list_only=True).programs.values():
            programs[format_name(program_name)] = program_name
        #all_files = [f for f in all_files if f in programs or f == 'default']
        
        page = 1
        limit = 10
        maximum = len(all_files)
        total_pages = round_up(maximum / limit)

        #Ask for user input
        while True:
            offset = (page - 1) * limit

            results = all_files[offset:offset + limit]
            for i, r in enumerate(results):
                try:
                    program_name = programs[r]
                except KeyError:
                    program_name = r
                print('{}: {}'.format(i + offset + 1, program_name))
            print('Page {} of {}. Type "page <number>" to switch.'.format(page, total_pages))
            print('You can type the number or name of a profile to load it.')

            profile = raw_input()
            last_page = page
            if profile.startswith('page '):
                try:
                    page = int(profile.split()[1])
                    if not 0 < page <= total_pages:
                        raise ValueError
                except IndexError:
                    print('Invalid page number')
                except ValueError:
                    if page > total_pages:
                        page = total_pages
                    else:
                        page = 1
            elif profile == '>':
                if page < total_pages:
                    page += 1
            elif profile == '<':
                if page > 1:
                    page -= 1
            else:
                try:
                    num = int(profile) - 1
                    if not 0 <= num <= maximum:
                        raise IndexError
                    try:
                        profile = programs[all_files[num]]
                    except KeyError:
                        profile = all_files[num]
                    break
                except ValueError:
                    break
                except IndexError:
                    print('Number doesn\'t match any profiles')


    try:
        current_profile = format_name(RunningPrograms().check()[0])
    except TypeError:
        pass
    else:
        selected_profile = format_name(profile)
        
        if current_profile == selected_profile:
            print('Warning: The profile you selected is currently running.')
            
            save_time = ticks_to_seconds(CONFIG['Save']['Frequency'], 1)
            metadata = load_program(profile, _metadata_only=True)
            if metadata['Modified'] is None:
                print('It has not had a chance to save yet, please wait a short while before trying again.')
                print('The saving frequency is currently set to {}.'.format(save_time))
                print('Press enter to exit.')
                raw_input()
                sys.exit()
            else:
                last_save_time = time.time() - metadata['Modified']
                next_save_time = CONFIG['Save']['Frequency'] - last_save_time
                last_save = ticks_to_seconds(last_save_time, 1, allow_decimals=False)
                next_save = ticks_to_seconds(next_save_time, 1, allow_decimals=False)
                print('It was last saved {} ago, so any tracks more recent than this will not be shown.'.format(last_save))
                print('The next save is due in roughly {}.'.format(next_save))


    generate_tracks = False
    generate_heatmap = False

    print('What do you want to generate?')
    print('Separate options with a space, or hit enter for all.')
    print('1: Tracks')
    print('2: Click Heatmap')

    result = simple_bit_mask(raw_input().split(), 2)

    if result[0]:
        generate_tracks = True
        
    if result[1]:
        
        generate_heatmap = True
        print('Which mouse buttons should be included in the heatmap?.')
        print('Separate options with a space, or hit enter for all.')
        print('1: Left Mouse Button')
        print('2: Middle Mouse Button')
        print('3: Right Mouse Button')
        heatmap_buttons = map(bool, simple_bit_mask(raw_input().split(), 3))
        CONFIG['GenerateHeatmap']['MouseButtonLeft'] = heatmap_buttons[0]
        CONFIG['GenerateHeatmap']['MouseButtonMiddle'] = heatmap_buttons[1]
        CONFIG['GenerateHeatmap']['MouseButtonRight'] = heatmap_buttons[2]
        if not heatmap_buttons:
            generate_heatmap = False


    if generate_tracks or generate_heatmap:
        print('Importing modules...')
        from core.image import RenderImage

        print('Loading profile {}...'.format(profile))
        r = RenderImage(profile)

        last_session_start = r.data['Ticks']['Session']['Total']
        last_session_end = r.data['Ticks']['Total']
        ups = CONFIG['Main']['UpdatesPerSecond']
        all_time = ticks_to_seconds(last_session_end, ups)
        last_session_time = ticks_to_seconds(last_session_end - last_session_start, ups)
        while True:
            print('Would you like to generate everything or just the last session?')
            print('1: Everything ({}) [Default]'.format(all_time))
            print('2: Last Session ({})'.format(last_session_time))

            result = simple_bit_mask(raw_input().split(), 2, default_all=False)
            if result[0] and result[1]:
                print('Please only select one option.')
            elif result[1]:
                last_session = True
                break
            else:
                last_session = False
                break

        #Generate
        if generate_tracks:
            r.generate('Tracks', last_session)
        if generate_heatmap:
            r.generate('Clicks', last_session)
    else:
        print('Nothing was set to generate.')

        
if __name__ == '__main__':
    user_generate()
