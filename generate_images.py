from __future__ import division
from multiprocessing import freeze_support
import time
import sys

from core.applications import RunningApplications, AppList
from core.compatibility import input, _print, get_items
from core.config import CONFIG
from core.constants import DEFAULT_NAME, UPDATES_PER_SECOND
from core.files import list_data_files, format_name, load_data
from core.input import value_select
from core.language import Language
from core.maths import round_up
from core.messages import ticks_to_seconds
    
    
def user_generate():
    """Ask for options and generate an image.
    This seriously needs rewriting.
    
    Idea:
        List of profiles (choose page/type id/type name), shows the file size and last modified date of each profile.
        (Load profile)
        Say some stats about the profile
        Ask for mouse tracks, clicks and key presses
        For each of those, ask for colour profile and say the file location
        Ask to open folder (will require image path rewrite for a base path)
        Loop back to start if required
    """
    CONFIG.save()
    
    all_strings = Language().get_strings()
    _string = all_strings['string']
    string = all_strings['string']['image']
    word = all_strings['word']

    _print(string['profile']['list'].format(L=word['list']))
    profile = input()

    if profile.lower() == word['list'].lower():

        #Read the data folder and format names
        all_files = list_data_files()
        if not all_files:
            _print(string['profile']['empty'])
            _print(all_strings['exit'])
            input()
            sys.exit()
        programs = {format_name(DEFAULT_NAME): DEFAULT_NAME}
        
        app_list = AppList()
        for program_name in app_list.names:
            programs[format_name(program_name)] = program_name
        
        page = 1
        limit = 15
        maximum = len(all_files)
        total_pages = round_up(maximum / limit)
        
        sort_date = string['page']['sort']['date']
        sort_name = string['page']['sort']['name']
        change_sort = [sort_name, 2]

        #Ask for user input
        while True:
            offset = (page - 1) * limit

            results = all_files[offset:offset + limit]
            for i, r in enumerate(results):
                try:
                    program_name = programs[r]
                except KeyError:
                    program_name = r
                _print('{}: {}'.format(i + offset + 1, program_name))
            _print(string['page']['current'].format(C=page, T=total_pages, P=word['page']))
            
            _print(change_sort[0].format(S='{} {}'.format(word['sort'], change_sort[1])))
            _print(string['profile']['number']['input'])

            profile = input()
            last_page = page
            
            #Change page
            if profile.lower().startswith('{P} '.format(P=word['page'])):
                try:
                    page = int(profile.split()[1])
                    if not 0 < page <= total_pages:
                        raise ValueError
                except IndexError:
                    _print(string['page']['invalid'])
                except ValueError:
                    if page > total_pages:
                        page = total_pages
                    else:
                        page = 1
                        
            #Shortcut to change page
            elif profile.endswith('>'):
                if page < total_pages:
                    page += 1
            elif profile.startswith('<'):
                if page > 1:
                    page -= 1
            
            #Change sorting of profile list
            elif (profile.lower().startswith('{} '.format(word['sort'])) 
                  or profile.lower() == word['sort']):
                try:
                    sort_level = int(profile.split()[1])
                except ValueError:
                    sort_level = 0
                except IndexError:
                    sort_level = 1
                try:
                    sort_reverse = int(profile.split()[2])
                except (ValueError, IndexError):
                    sort_reverse = 0
                if sort_level == 1:
                    all_files = list_data_files()
                    change_sort = [sort_name, 2]
                elif sort_level == 2:
                    all_files = sorted(list_data_files())
                    change_sort = [sort_date, 1]
                if sort_reverse:
                    all_files = all_files[::-1]
            
            #Select profile
            else:
                try:
                    num = int(profile) - 1
                    if not 0 <= num <= maximum:
                        raise IndexError
                    profile_name = all_files[num]
                    try:
                        profile = programs[all_files[num]]
                    except KeyError:
                        profile = all_files[num]
                    break
                except ValueError:
                    break
                except IndexError:
                    _print(string['profile']['number']['nomatch'])

        try:
            profile = programs[profile]
        except KeyError:
            pass
    
    #Load functions
    _print(_string['import'])
    from core.image import RenderImage

    _print(_string['profile']['load'].format(P=profile))
    try:
        r = RenderImage(profile)
    except ValueError:
        _print('Error: Selected profile is empty or doesn\'t exist.')
        return
    
    #Check if profile is running
    try:
        current_profile = format_name(RunningApplications().check()[0])
    except TypeError:
        pass
    else:
        selected_profile = format_name(profile)
        
        if current_profile == selected_profile:
            _print(string['profile']['running']['warning'])
            
            save_time = ticks_to_seconds(CONFIG['Save']['Frequency'], 1)
            metadata = load_data(profile, _metadata_only=True)
            if metadata['Modified'] is None:
                _print(string['save']['wait'])
                _print(string['save']['frequency'].format(T=save_time))
                _print(_string['exit'])
                input()
                sys.exit()
            else:
                last_save_time = time.time() - metadata['Modified']
                next_save_time = CONFIG['Save']['Frequency'] - last_save_time
                last_save = ticks_to_seconds(last_save_time, 1, allow_decimals=False)
                next_save = ticks_to_seconds(next_save_time, 1, allow_decimals=False)
                _print(string['save']['next'].format(T1=last_save, T2=next_save))


    generate_tracks = False
    generate_heatmap = False
    generate_keyboard = False
    generate_csv = False
    
    default_options = [True, True, True, False]
    
    kb_string = string['name']['keyboard']
    kph = r.keys_per_hour()
    if kph < 10:
        default_options[2] = False
        kb_string = '{} ({} {})'.format(kb_string, 
                                        string['name']['low']['keyboard'], 
                                        string['name']['low']['steam']).format(C=round(kph, 2))
    
    _print(string['option']['generate'])
    default_option_text = ' '.join(str(i+1) for i, v in enumerate(default_options) if v)
    _print(string['option']['select'].format(V=default_option_text))
    _print('1: {}'.format(string['name']['track']))
    _print('2: {}'.format(string['name']['click']))
    _print('3: {}'.format(kb_string))
    _print('4: {}'.format(string['name']['csv']))
    
    selection = list(map(int, input().split()))
    result = value_select(selection, default_options, start=1)
    
    if result[0]:
        generate_tracks = True
        
    if result[1]:
        
        generate_heatmap = True
        _print('Which mouse buttons should be included in the heatmap?.')
        
        default_options = [CONFIG['GenerateHeatmap']['_MouseButtonLeft'], 
                           CONFIG['GenerateHeatmap']['_MouseButtonMiddle'],
                           CONFIG['GenerateHeatmap']['_MouseButtonRight']]
        default_option_text = ' '.join(str(i+1) for i, v in enumerate(default_options) if v)
        _print(string['option']['select'].format(V=default_option_text))
        
        _print('1: {}'.format(word['mousebutton']['left']))
        _print('2: {}'.format(word['mousebutton']['middle']))
        _print('3: {}'.format(word['mousebutton']['right']))
        selection = list(map(int, input().split()))
        heatmap_buttons = value_select(selection, default_options, start=1)
        CONFIG['GenerateHeatmap']['_MouseButtonLeft'] = heatmap_buttons[0]
        CONFIG['GenerateHeatmap']['_MouseButtonMiddle'] = heatmap_buttons[1]
        CONFIG['GenerateHeatmap']['_MouseButtonRight'] = heatmap_buttons[2]
        if not any(heatmap_buttons):
            generate_heatmap = False

    if result[2]:
        generate_keyboard = True
        
    if result[3]:
        generate_csv = True

    if generate_tracks or generate_heatmap or generate_keyboard or generate_csv:

        last_session_start = r.data['Ticks']['Session']['Total']
        last_session_end = r.data['Ticks']['Total']
        all_time = ticks_to_seconds(last_session_end, UPDATES_PER_SECOND)
        last_session_time = ticks_to_seconds(last_session_end - last_session_start, UPDATES_PER_SECOND)
        
        csv_only = generate_csv and not any((generate_tracks, generate_heatmap, generate_keyboard))
        if not last_session_time or last_session_time == all_time or csv_only:
            last_session = False
        
        else:
            while True:
                _print(string['option']['session']['select'])
                
                _print('1: {} [{}]'.format(string['option']['session']['all'].format(T=all_time), word['default']))
                _print('2: {}'.format(string['option']['session']['last'].format(T=last_session_time)))

                selection = list(map(int, input().split()))
                result = value_select(selection, [True, False], start=1)
                if result[0] and result[1]:
                    _print(string['option']['error']['single'])
                elif result[1]:
                    last_session = True
                    break
                else:
                    last_session = False
                    break

        #Generate
        if generate_tracks:
            r.tracks(last_session)
        if generate_heatmap:
            r.clicks(last_session)
        if generate_keyboard:
            r.keyboard(last_session)
        if generate_csv:
            r.csv()
            
    else:
        _print(string['option']['error']['nothing'])

        
if __name__ == '__main__':
    freeze_support()
    user_generate()
