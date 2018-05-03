"""
This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""

from __future__ import absolute_import

import codecs

import core.utf8
from core.base import get_script_file
from core.config import CONFIG
from core.constants import DEFAULT_LANGUAGE


ALLOWED_CHARACTERS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_'

LANGUAGE_FOLDER = 'language'

KEYBOARD_LAYOUT_FOLDER = 'keyboard_layout'

CONSOLE_STRINGS_FOLDER = 'console' #Being phased out

STRINGS_FOLDER = 'strings'

LANGUAGE_BASE_PATH = get_script_file(LANGUAGE_FOLDER)


def follow_file_links(file_name, extension, path, visited=None):
    """Follow paths recursively if they contain a link to another file."""
    
    #Check for recursion
    if visited is None:
        visited = set()
    if file_name in visited:
        raise IOError('recursion in file links')
    visited.add(file_name)
    
    #Read the file
    try:
        with codecs.open('{}/{}.{}'.format(path, file_name, extension), 'r', 'utf-8') as f:
            read_data = f.read()
            if ord(read_data[0]) == 65279: #Remove dumb utf-8 marker that won't disappear
                read_data = read_data[1:]
            data = read_data.strip().splitlines()
    except IOError:
        data = []
    else:
        if data and data[0][0].lstrip() == '<' and data[0][-1].rstrip() == '>':
            return follow_file_links(data[0][1:-1], extension, path, visited)
    return data


class Language(object):

    def __init__(self, language=CONFIG['Main']['Language'], fallback_language=DEFAULT_LANGUAGE):
        self.strings = None
        self.keyboard = None
    
        #Read from chosen file, then backup file if needed
        language_order = (language, fallback_language)
        for language in language_order:
        
            #Get the string and keyboard languages to use
            links = follow_file_links(language, 'txt', LANGUAGE_BASE_PATH)
            for link in links:
                var, value = [i.strip() for i in link.split('=')]
                link_parts = var.split('.')
                if link_parts[0] == 'locale':
                    if link_parts[1] == 'strings':
                        self.strings = value.strip()
                    elif link_parts[1] == 'keyboard':
                        if link_parts[2] == 'layout':
                            self.keyboard = value.strip()
            if self.strings is not None and self.keyboard is not None:
                break
        
        if self.strings is None or self.keyboard is None:
            raise IOError('no language file found in the folder "{}\\"'.format(LANGUAGE_BASE_PATH))
                
        
    def get_keyboard_layout(self, extended=True):
        keyboard_layout = []
        
        keyboard_layout_folder = '{}/{}'.format(LANGUAGE_BASE_PATH, KEYBOARD_LAYOUT_FOLDER)
        try:
            data = follow_file_links(self.keyboard, 'txt', keyboard_layout_folder)
        except AttributeError:
            return []
            
        try:
            gap = float(data[0])
        except ValueError:
            gap = 1
        else:
            del data[0]
        
        for row in data:
            keyboard_layout.append([])
            
            #Handle half rows
            row = row.strip()
            if not row:
                continue
            
            #Remove second half of keyboard if required
            if extended:
                row = row.replace(':', '')
            else:
                row = row.split(':', 1)[0]
            
            for key in row.split('+'):
            
                key_data = key.split('|')
                default_height = 1
                default_width = 1
                
                #Get key name if set, otherwise change the width
                try:
                    name = str(key_data[0])
                    if not name:
                        name = None
                        raise IndexError
                except IndexError:
                    default_width = gap
                
                #Set width and height
                try:
                    width = float(key_data[1])
                except (IndexError, ValueError):
                    width = default_width
                else:
                    width = max(0, width)
                try:
                    height = float(key_data[2])
                except (IndexError, ValueError):
                    height = default_height
                else:
                    height = max(0, height)
                
                keyboard_layout[-1].append([name, width, height])
                
        return keyboard_layout
    
    def get_strings(self):
        try:
            data = follow_file_links(self.strings, 'txt', '{}/{}'.format(LANGUAGE_BASE_PATH, CONSOLE_STRINGS_FOLDER))
        except AttributeError:
            return {}
        strings = {}
        
        for line in data:
            try:
                var, value = [i.strip() for i in line.split('=', 1)]
            except ValueError:
                pass
            else:
                var_parts = var.split('.')
                var_len = len(var_parts)
                if var_len == 1:
                    continue
                
                #Recursively look down dictionary
                _strings = strings
                for i, part in enumerate(var_parts[:-1]):
                    last_loop = i == var_len - 2
                    try:
                        if not last_loop:
                            _strings = _strings[part]
                    except KeyError:
                        _strings[part] = {}
                        if not last_loop:
                            _strings = _strings[part]
                        
                try:
                    _strings[part][var_parts[-1]] = value.replace('\\n', '\n')
                except KeyError:
                    _strings[part] = {var_parts[-1]: value.replace('\\n', '\n')}
        
        return strings



from core.compatibility import iteritems
from core.ini import Config

LANGUAGE_DEFAULTS = {
    'Words': {
        'Default': {
            '__info__': 'Used for showing options, does not affect the name of the default profile.',
            'value': 'Default'
        },
        'Page': 'page',
        'Sort': 'sort',
        'And': 'and',
        'TimeSecondSingle': 'second',
        'TimeSecondPlural': 'seconds',
        'TimeMinuteSingle': 'minute',
        'TimeMinutePlural': 'minutes',
        'TimeHourSingle': 'hour',
        'TimeHourPlural': 'hours',
        'TimeDaySingle': 'day',
        'TimeDayPlural': 'days',
        'TimeWeekSingle': 'week',
        'TimeWeekPlural': 'weeks',
        'TimeYearSingle': 'year',
        'TimeYearPlural': 'years',
        'CommandSingle': 'command',
        'CommandPlural': 'commands',
        'PressSingle': 'press',
        'PressPlural': 'presses',
        'ReleaseSingle': 'release',
        'ReleasePlural': 'releases',
        'KeyboardKeySingle': 'key',
        'KeyboardKeyPlural': 'keys',
        'GamepadButtonSingle': 'button',
        'GamepadButtonPlural': 'buttons',
    },
    'Misc': {
        'UserChoice': 'Type your choice here:',
        'ImportFailed': {
            '__info__': 'Valid Replacements: [MODULE] [REASON]',
            'value': 'Import of [MODULE] failed. Reason: "[REASON]".'
        },
        'ProfileLoad': {
            '__info__': 'Valid Replacements: [PROFILE]',
            'value': 'Loading profile [PROFILE]...'
        },
        'ProgramError': 'An error occurred.',
        'ProgramExit': 'Press enter to exit.',
        'ProgramRestart': 'Please restart the program.',
        'OpenImageFolder': 'Opening image folder...',
    },
    'Internet': {
        'Request': {
            '__info__': 'Valid Replacements: [URL]',
            'value': 'Sent request to [URL].',
            'level': 1
        }
    },
    'Server': {
        'FlaskStart': {
            'value': 'Starting web server...',
            'level': 2
        },
        'FlaskPort': {
            '__info__': 'Valid Replacements: [PORT]',
            'value': 'Bound web connection to port [PORT].',
            'level': 2
        },
        'MessageStart': {
            'value': 'Starting message server...',
            'level': 2
        },
        'MessagePort': {
            '__info__': 'Valid Replacements: [PORT]',
            'value': 'Bound message connection to port [PORT].',
            'level': 2
        },
        'MessageSecretSet': {
            '__info__': 'Valid Replacements: [SECRET]',
            'value': 'The code required to connect to the message server is "[SECRET]".',
            'level': 1
        },
        'MessageListen': {
            'value': 'Waiting for new connection...',
            'level': 1
        },
        'MessageConnection': {
            '__info__': 'Valid Replacements: [HOST] [PORT]',
            'value': 'Connection from [HOST]:[PORT] made to application.',
            'level': 2
        },
        'PortTaken': {
            '__info__': 'Valid Replacements: [PORT]',
            'value': 'Port [PORT] currently in use.',
            'level': 1
        },
        'PortClose': {
            '__info__': 'Valid Replacements: [PORT]',
            'value': 'Closing process to free port....',
            'level': 1
        },
        'PortRandom': {
            'value': 'Selecting random port...',
            'level': 1
        }
    },
    'Mouse': {
        'MouseButtonLeft': 'Left mouse button',
        'MouseButtonMiddle': 'Middle mouse button',
        'MouseButtonRight': 'Right mouse button',
        'MousebuttonThumb1': 'Thumb button 1',
        'MousebuttonThumb2': 'Thumb button 2',
        'MouseClickSingle': 'clicked',
        'MouseClickDouble': 'double clicked'
    },
    'Tracking': {
        'ProfileNew': {
            'value': 'Started recording to new file.',
            'level': 1
        },
        'ProfileLoad': {
            'value': 'Finished loading data.',
            'level': 1
        },
        'ScriptResume': {
            'value': 'Resumed tracking.',
            'level': 2
        },
        'ScriptPause': {
            'value': 'Paused tracking.',
            'level': 2
        },
        'ScriptStop': {
            'value': 'Ending program...',
            'level': 2
        },
        'ScriptRestart': {
            'value': 'Restarting program...',
            'level': 2
        },
        'ScriptMainStart': {
            'value': 'Main process started.',
            'level': 2
        },
        'ScriptThreadStart':{
            'value': 'Background process started.',
            'level': 2
        },
        'ScriptMainEnd': {
            'value': 'Main process quit.',
            'level': 2
        },
        'ScriptThreadEnd': {
            'value': 'Background process quit.',
            'level': 2
        },
        'ScriptPath': {
            '__info__': 'Valid Replacements: [DOCUMENTS-PATH]',
            'value': 'Set save location to "[DOCUMENTS-PATH]".',
            'level': 2
        },
        'ScriptDuplicate': {
            'value': 'Another instance of the program is already running.'
        },
        'ScriptQueueSize': {
            '__info__': 'Valid Replacements: [NUMBER] [COMMANDS-PLURAL]',
            'value': '[NUMBER] [COMMANDS-PLURAL] queued for processing.',
            'level': 1
        },
        'ApplicationStart': {
            '__info__': 'Valid Replacements: [APPLICATION-NAME]',
            'value': 'Application detected: [APPLICATION-NAME]',
            'level': 2
        },
        'ApplicationEnd': {
            '__info__': 'Valid Replacements: [APPLICATION-NAME]',
            'value': 'Application quit: [APPLICATION-NAME]',
            'level': 2
        },
        'ApplicationFocused': {
            '__info__': 'Valid Replacements: [APPLICATION-NAME]',
            'value': 'Application gained focus: [APPLICATION-NAME]',
            'level': 2
        },
        'ApplicationUnfocused': {
            '__info__': 'Valid Replacements: [APPLICATION-NAME]',
            'value': 'Application lost focus: [APPLICATION-NAME]',
            'level': 2
        },
        'ApplicationLoad': {
            '__info__': 'Valid Replacements: [APPLICATION-NAME]',
            'value': 'Switching profile to [APPLICATION-NAME].',
            'level': 2
        },
        'ApplicationListen': {
            'value': 'Started checking for running applications.',
            'level': 1
        },
        'AppListReload': {
            '__info__': 'Valid Replacements: [FILE-NAME]',
            'value': 'Reloaded [FILE-NAME].',
            'level': 1
        },
        'AppListDownload': {
            '__info__': 'Valid Replacements: [FILE-NAME] [URL]',
            'value': 'Updating [FILE-NAME] from [URL]...',
            'level': 1
        },
        'AppListDownloadSuccess': {
            '__info__': 'Valid Replacements: [FILE-NAME] [URL]',
            'value': 'Completed update.',
            'level': 1
        },
        'AppListDownloadFail': {
            '__info__': 'Valid Replacements: [FILE-NAME] [URL]',
            'value': 'Failed to establish a connection.',
            'level': 1
        },
        'CompressStart': {
            '__info__': 'Valid Replacements: [TRACK-TYPE]',
            'value': 'Data is being compressed for [TRACK-TYPE]...',
            'level': 1
        },
        'CompressEnd': {
            '__info__': 'Valid Replacements: [TRACK-TYPE]',
            'value': 'Finished compressing data.',
            'level': 1
        },
        'SavePrepare': {
            'value': 'Preparing data to save...',
            'level': 2
        },
        'SaveStart': {
            'value': 'Saving the file...',
            'level': 2
        },
        'SaveComplete': {
            'value': 'Finished saving.',
            'level': 2
        },
        'SaveIncompleteNoRetry': {
            'value': 'Unable to save file, make sure this has the correct permissions.',
            'level': 2
        },
        'SaveIncompleteRetry': {
            '__info__': 'Valid Replacements: [ATTEMPT-CURRENT] [ATTEMPT-MAX] [SECONDS] [SECONDS-PLURAL] [MINUTES] [MINUTES-PLURAL]',
            'value': 'Unable to save file, trying again in [SECONDS] [SECONDS-PLURAL] (attempt [ATTEMPT-CURRENT] of [ATTEMPT-MAX]).',
            'level': 2
        },
        'SaveIncompleteRetryFail': {
            'value': 'Failed to save file (maximum attempts reached), make sure the correct permissions have been granted.',
            'level': 2
        },
        'SaveSkipInactivity': {
            'value': 'Skipping save due to inactivity, (last save was [SECONDS] [SECONDS-PLURAL] ago).',
            'level': 2
        },
        'SaveSkipNoChange': {
            'value': 'Skipping save - nothing has been processed yet since the last save.',
            'level': 2
        },
        'ResolutionNew': {
            '__info__': 'Valid Replacements: [XRES-OLD] [YRES-OLD] [XRES] [YRES]',
            'value': 'Resolution changed from [XRES-OLD]x[YRES-OLD] to [XRES]x[YRES].',
            'level': 2
        },
        'ResolutionChanged': {
            '__info__': 'Valid Replacements: [XRES-OLD] [YRES-OLD] [XRES] [YRES]',
            'value': 'Mouse moved to [YRES]p screen.',
            'level': 1
        },
        'ResolutionAppLoad': {
            '__info__': 'Valid Replacements: [XRES] [YRES]',
            'value': 'Application resolution is [XRES]x[YRES].',
            'level': 1
        },
        'ResolutionAppResize': {
            '__info__': 'Valid Replacements: [XRES-OLD] [YRES-OLD] [XRES] [YRES]',
            'value': 'Application resized from [XRES-OLD]x[YRES-OLD] to [XRES]x[YRES].',
            'level': 1
        },
        'ResolutionAppMove': {
            '__info__': 'Valid Replacements: [XRES-OLD] [YRES-OLD] [XRES] [YRES]',
            'value': 'Application moved from ([XPOS-OLD], [YPOS-OLD]) to ([XPOS], [YPOS]).',
            'level': 1
        },
        'MousePosition': {
            '__info__': 'Valid Replacements: [XPOS] [YPOS]',
            'value': 'Cursor Position: ([XPOS], [YPOS])',
            'level': 0
        },
        'MouseVisible': {
            'value': 'Cursor has entered the main monitor.',
            'level': 1
        },
        'MouseInvisible': {
            'value': 'Cursor has left the main monitor.',
            'level': 1
        },
        'MouseDetected': {
            'value': 'Cursor position has been detected.',
            'level': 2
        },
        'MouseUndetected': {
            'value': 'Unable to read cursor position.',
            'level': 2
        },
        'MouseClickedVisible': {
            '__info__': 'Valid Replacements: [MOUSEBUTTON] [CLICKED] [XPOS] [YPOS]',
            'value': '[MOUSEBUTTON] [CLICKED] at ([XPOS], [YPOS]).',
            'level': 1
        },
        'MouseClickedInvisible': {
            '__info__': 'Valid Replacements: [MOUSEBUTTON] [CLICKED]',
            'value': '[MOUSEBUTTON] [CLICKED].',
            'level': 1
        },
        'MouseHeldVisible': {
            '__info__': 'Valid Replacements: [MOUSEBUTTON] [XPOS] [YPOS]',
            'value': '[MOUSEBUTTON] being held at ([XPOS], [YPOS]).',
            'level': 1
        },
        'MouseHeldInvisible': {
            '__info__': 'Valid Replacements: [MOUSEBUTTON]',
            'value': '[MOUSEBUTTON] being held.',
            'level': 1
        },
        'MouseClickedRelease': {
            'value': 'Mouse button released.',
            'level': 0
        },
        'KeyboardPressed': {
            '__info__': 'Valid Replacements: [KEY-PLURAL], [PRESS-PLURAL], [KEYS]',
            'value': '[KEY-PLURAL] pressed: [KEYS]',
            'level': 1
        },
        'KeyboardHeld': {
            '__info__': 'Valid Replacements: [KEY-PLURAL], [PRESS-PLURAL], [KEYS]',
            'value': '[KEY-PLURAL] pressed (held down): [KEYS]',
            'level': 1
        },
        'KeyboardReleased': {
            '__info__': 'Valid Replacements: [KEY-PLURAL], [RELEASE-PLURAL], [KEYS]',
            'value': '[KEY-PLURAL] released',
            'level': 0
        },
        'GamepadConnected': {
            '__info__': 'Valid Replacements: [ID]',
            'value': 'Detected new gamepad ([ID]).',
            'level': 2
        },
        'GamepadDisconnected': {
            '__info__': 'Valid Replacements: [ID]',
            'value': 'Lost connection to gamepad [ID].',
            'level': 2
        },
        'GamepadButtonPressed': {
            '__info__': 'Valid Replacements: [ID] [BUTTON-PLURAL] [BUTTONS]',
            'value': 'Gamepad [ID]: pressed [BUTTON-PLURAL] [BUTTONS]',
            'level': 1
        },
        'GamepadButtonHeld': {
            '__info__': 'Valid Replacements: [ID] [BUTTON-PLURAL] [BUTTONS]',
            'value': 'Gamepad [ID]: holding [BUTTON-PLURAL] [BUTTONS]',
            'level': 1
        },
        'GamepadButtonHeld': {
            '__info__': 'Valid Replacements: [ID] [BUTTON-PLURAL] [BUTTONS]',
            'value': 'Gamepad [ID]: released [BUTTON-PLURAL] [BUTTONS]',
            'level': 0
        },
        'GamepadAxis': {
            '__info__': 'Valid Replacements: [ID] [AXIS] [VALUE]',
            'value': 'Gamepad [ID]: [AXIS] set to [VALUE]',
            'level': 0
        }
    },
    'RenderTypes': {
        'Tracks': 'Tracks',
        'Speed': 'Acceleration',
        'Strokes': 'Brush Strokes',
        'Clicks': 'Click Heatmap',
        'Keyboard': 'Keyboard Heatmap'
    },
    'GenerationInput': {
        'KeyboardNoUse': {
            '__info__': 'Valid Replacements: [KEYS-PER-HOUR]',
            'value': 'The keyboard doesn\'t appear to have been tracked for this application.'
        },
        'NoSelection': 'Error: Nothing was chosen, would you like to restart?',
        'GenerateChoice': 'What do you want to generate?',
        'OptionsForRender': {
            '__info__': 'Valid Replacements: [RENDER-TYPE]',
            'value': 'Options for [RENDER-TYPE]...'
        },
        'ColourNotSet': 'Colour scheme is not set in the config, either type your own (check readme.txt for info) or use these presets.\nLeave empty to use a random selection, or separate the options with a space or comma.',
        'SessionSelect': 'Would you like to generate everything or just the last session?',
        'SessionAll': {
            '__info__': 'Valid Replacements: [TIME]',
            'value': 'Everything ([TIME])'
        },
        'SessionLatest': {
            '__info__': 'Valid Replacements: [TIME]',
            'value': 'Last Session ([TIME])'
        },
        'SeparateOptions': {
            '__info__': 'Valid Replacements: [ID] [VALUE]',
            'value': 'Separate the options with a space or comma, or hit enter for the default of "[ID]" ([VALUE])'
        },
        'SelectProfile': 'Select a profile by typing its name or the matching ID.',
        'ProfileIndexError': {
            '__info__': 'Valid Replacements: [NEW-INDEX] [INDEX-MIN] [INDEX-MAX]',
            'value': 'Error: Invalid profile index: [NEW-INDEX] (must be between [INDEX-MIN]-[INDEX-MAX])'
        },
        'ProfileEmpty': {
            '__info__': 'Valid Replacements: [PROFILE]',
            'value': 'Error: Profile doesn\'t exist.'
        },
        'ProfileRunning': {
            '__info__': 'Valid Replacements: [PROFILE]',
            'value': 'Warning: The profile you selected is currently running.'
        },
        'ProfileSaveNew': {
            '__info__': 'Valid Replacements: [PROFILE]',
            'value': 'It has not had a chance to save yet, please wait before trying again.'
        },
        'ProfileSaveNext': {
            '__info__': 'When the next save will be. Valid Replacements: [PROFILE] [PREVIOUS-SAVE] [NEXT-SAVE]',
            'value': 'The last save was [PREVIOUS-SAVE] ago, so any tracks more recent than this will not be shown.\nThe next save is due in roughly [NEXT-SAVE].'
        },
        'ProfileSaveDue': {
            '__info__': 'When a save should have happened. Valid Replacements: [PROFILE] [PREVIOUS-SAVE] [NEXT-SAVE]',
            'value': 'The last save was [PREVIOUS-SAVE] ago, so any tracks more recent than this will not be shown.\nThe next save should have been due [NEXT-SAVE] age.'
        },
        'SaveFrequency': {
            '__info__': 'Valid Replacements: [TIME]',
            'value': 'The saving frequency is currently set to [TIME].'
        },
        'PageSort': {
            '__info__': 'Valid Replacements: [SORT-TYPE] [ORDER]',
            'value': 'Files are being sorted by "[SORT-TYPE] - [ORDER]".'
        },
        'PageSortSelect': {
            '__info__': 'Valid Replacements: [SORT](required) [SORT-OPTIONS]',
            'value': 'Type "[SORT] <ID>" to change or reverse the sorting method. Possible options are [SORT-OPTIONS].'
        },
        'PageSortInvalidID': {
            '__info__': 'Valid Replacements: [CURRENT-SORT] [NEW-SORT] [SORT-MIN] [SORT-MAX]',
            'value': 'Error: Invalid sorting ID: [NEW-SORT] (must be between [SORT-MIN]-[SORT-MAX])'
        },
        'PageSortInvalidType': {
            '__info__': 'Valid Replacements: [CURRENT-SORT] [NEW-SORT] [SORT-OPTIONS]',
            'value': 'Error: Invalid sorting type: [NEW-SORT]'
        },
        'PageSortReverse': 'Reversed sorting.',
        'PageSortNew': {
            '__info__': 'Valid Replacements: [SORT-TYPE]',
            'value': 'List sorting changed to [SORT-TYPE]'
        },
        'PageNumber': {
            '__info__': 'Valid Replacements: [CURRENT-PAGE] [TOTAL-PAGES] [PAGE](required)',
            'value': 'Page [CURRENT-PAGE] of [TOTAL-PAGES]. Type "[PAGE] <number>" to switch.'
        },
        'PageNumberInvalid': {
            '__info__': 'Valid Replacements: [PAGE] [TOTAL-PAGES] [PAGE](required)',
            'value': 'Error: Invalid page number: [PAGE] (must be between [PAGE-MIN]-[PAGE-MAX])'
        }
    },
    'Generation': {
        'ImageSaveStart': {
            '__info__': 'Valid Replacements: [IMAGE-PATH] [IMAGE-NAME]',
            'value': 'Saving image to "[IMAGE-PATH]".'
        },
        'ImageSaveEnd': {
            '__info__': 'Valid Replacements: [IMAGE-PATH] [IMAGE-NAME]',
            'value': 'Finished saving image.'
        },
        'ImageSaveFail': {
            '__info__': 'Valid Replacements: [IMAGE-PATH] [IMAGE-NAME] [REASON]',
            'value': 'Error: Failed to save image ([REASON]).'
        },
        'KeyboardGenerateLayout': 'Building keyboard from layout...',
        'KeyboardGenerateCoordinates': 'Generating coordinates...',
        'KeyboardDrawShadow': 'Adding shadow...',
        'KeyboardDrawColour': 'Colouring keys...',
        'KeyboardDrawOutline': 'Drawing outlines...',
        'KeyboardDrawText': 'Writing text...',
        'KeyboardDrawOutline': 'Drawing outlines...',
        'KeyboardStatsColourCount': 'Colour based on number of key presses.',
        'KeyboardStatsColourTime': 'Colour based on how long keys were pressed for.',
        'KeyboardStatsCount': {
            '__info__': 'Valid Replacements: [NUMBER]',
            'value': 'Total key presses: [NUMBER]'
        },
        'KeyboardStatsTime': {
            '__info__': 'Valid Replacements: [TIME]',
            'value': 'Time elapsed: [TIME]'
        }
    }
}


STRINGS = Config(LANGUAGE_DEFAULTS, default_settings={'type': str, 'allow_empty': False})#.load(LANGUAGE_PATH, LANGUAGE_PATH_DEFAULT)