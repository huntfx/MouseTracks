# -*- coding: utf-8 -*-
"""This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""
#Define and load the strings used around the program

from __future__ import absolute_import

import codecs
import os

import core.utf8
from core.base import get_script_file
from core.compatibility import iteritems
from core.config import CONFIG
from core.constants import DEFAULT_LANGUAGE
from core.ini import Config


LANGUAGE_FOLDER = 'language'

KEYBOARD_LAYOUT_FOLDER = 'keyboard_layout' #Being phased out

STRINGS_FOLDER = 'strings'

KEYBOARD_FOLDER = 'keyboard'

LANGUAGE_BASE_PATH = get_script_file(LANGUAGE_FOLDER)

LANGUAGE_DEFAULTS = {
    'Words': {
        '__priority__': 1,
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
    'Input': {
        '__priority__': 2,
        'UserChoice': 'Type your choice here:',
        'PortConnect': 'Type a port to connect to:',
        'PortPassword': 'Type the password to decode the messages:'
    },
    'Misc': {
        '__priority__': 2,
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
        '__priority__': 4,
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
        },
        'MessageServerNotRunning': 'Server appears to have stopped.',
        'MessageServerIncorrectPassword': 'Incorrect password provided',
        'MessageServerDecryptError': 'Unable to decrypt message.'
    },
    'Mouse': {
        '__priority__': 4,
        'ButtonLeft': 'Left mouse button',
        'ButtonMiddle': 'Middle mouse button',
        'ButtonRight': 'Right mouse button',
        'ButtonThumb1': 'Thumb button 1',
        'ButtonThumb2': 'Thumb button 2',
        'ClickSingle': 'clicked',
        'ClickDouble': 'double clicked'
    },
    'Tracking': {
        '__priority__': 5,
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
        'AppListDownloadStart': {
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
            '__info__': 'Valid Replacements: [SECONDS] [SECONDS-PLURAL] [MINUTES] [MINUTES-PLURAL] [HOURS] [HOURS-PLURAL]',
            'value': 'Skipping save due to inactivity, (last save was [MINUTES] [MINUTES-PLURAL] ago).',
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
        '__priority__': 2,
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
        'PageSortReverse': {
            '__info__': 'Valid Replacements: [SORT-TYPE]',
            'value': 'Reversed sorting for [SORT-TYPE].'
        },
        'PageSortNew': {
            '__info__': 'Valid Replacements: [SORT-TYPE]',
            'value': 'List sorting changed to [SORT-TYPE].'
        },
        'PageNumber': {
            '__info__': 'Valid Replacements: [CURRENT-PAGE] [TOTAL-PAGES] [PAGE](required)',
            'value': 'Page [CURRENT-PAGE] of [TOTAL-PAGES]. Type "[PAGE] <number>" to switch.'
        },
        'PageNumberInvalid': {
            '__info__': 'Valid Replacements: [CURRENT-PAGE] [NEW-PAGE] [TOTAL-PAGES] [PAGE]',
            'value': 'Error: Invalid page number: [NEW-PAGE] (must be between [PAGE-MIN]-[PAGE-MAX])'
        },
        'RenderOptions': {
            '__info__': 'Valid Replacements: [RENDER-TYPE]',
            'value': 'Options for [RENDER-TYPE]...'
        },
        'ColourMapInvalid': {
            '__info__': 'If the user sets an invalid colour map. Valid Replacements: [COLOUR-MAP]',
            'value': '"[COLOUR-MAP]" is not a valid colour map.'
        },
        'ColourMapNotSet': {
            '__info__': 'This is displayed if no colour maps were valid, user either makes another choice or leaves empty for a random choice.',
            'value': 'Error: No valid colour maps in selection. Please make another choice or leave empty for a random choice.'
        },
        'MouseButtonSelection': 'Which mouse buttons should be included in the heatmap?',
        'MouseButtonNotSet': 'No mouse buttons were selected, disabling heatmap.',
        'OptionChosenSingle': {
            '__info__': 'Valid Replacements: [OPTION]',
            'value': '[OPTION] was chosen.'
        },
        'OptionChosenMultiple': {
            '__info__': 'Valid Replacements: [OPTION]',
            'value': '[OPTION] have been chosen.'
        },
        'OptionRandomSingle': {
            '__info__': 'Valid Replacements: [OPTION]',
            'value': '[OPTION] was chosen at random.'
        },
        'OptionRandomMultiple': {
            '__info__': 'Valid Replacements: [OPTION]',
            'value': '[OPTION] have been chosen at random.'
        },
        'OptionInvalidSingleChoice': {
            '__info__': 'Valid Replacements: [OPTION-COUNT]',
            'value': 'Error: Only one option can be chosen.'
        },
        'OptionInvalidInput': {
            '__info__': 'Generic error if none of the chosen options match anything.',
            'value': 'Error: Invalid choice.'
        },
        'OptionValid': {
            '__info__': 'Valid Replacements: [OPTION]',
            'value': '[OPTION] was chosen.'
        },
        'ListItem': {
            '__info__': 'General list item. Valid Replacements: [ID] [OPTION]',
            'value': '[ID]: [OPTION]'
        },
        'ListItemDefault': {
            '__info__': 'General list item, acts as default if no other choice is made. Valid Replacements: [ID] [OPTION]',
            'value': '[ID]: [OPTION] [Default]'
        },
        'GenerateCSV': {
            '__info__': 'Valid Replacements: [RENDER-TYPE]',
            'value': 'Generating CSV from [RENDER-TYPE]...'
        }
    },
    'Generation': {
        '__priority__': 7,
        'NoData': 'No tracking data found.',
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
        },
        'UpscaleArrayStart': {
            '__info__': 'Valid Replacements: [XRES] [YRES]',
            'value': 'Upscaling arrays to [XRES]x[YRES]...'
        },
        'UpscaleArrayProgress': {
            '__info__': 'Valid Replacements: [XRES] [YRES] [CURRENT] [TOTAL]',
            'value': 'Processing array for [XRES]x[YRES] ([CURRENT]/[TOTAL])'
        },
        'ArrayMerge': {
            '__info__': 'The stored arrays need to be merged together.',
            'value': 'Merging arrays...'
        },
        'ArrayRemap': {
            '__info__': 'For heatmaps the values are mapped to a linear range (it always becomes "0, 1, 2...").',
            'value': 'Remapping values...'
        },
        'ArrayBlur': 'Applying gaussian blur...',
        'ArrayRange': {
            '__info__': 'The range just means the minimum and maximum values contained within the array.',
            'value': 'Finding range limits...'
        },
    },
    'Keys': {
        8: {
            '__info__': 'Keyboard key for Backspace.',
            'value': 'Back'
        },
        9: {
            '__info__': 'Keyboard key for Tab.',
            'value': 'Tab'
        },
        13: {
            '__info__': 'Keyboard key for Enter/Return.',
            'value': 'Return'
        },
        20: {
            '__info__': 'Keyboard key for Caps Lock.',
            'value': 'Caps Lock'
        },
        27: {
            '__info__': 'Keyboard key for Escape.',
            'value': 'Esc'
        },
        32: {
            '__info__': 'Keyboard key for Space.',
            'value': 'Space'
        },
        33: {
            '__info__': 'Keyboard key for Page Up.',
            'value': 'Page\nUp'
        },
        34: {
            '__info__': 'Keyboard key for Page Down.',
            'value': 'Page\nDown'
        },
        35: {
            '__info__': 'Keyboard key for End.',
            'value': 'End'
        },
        36: {
            '__info__': 'Keyboard key for Home.',
            'value': 'Home'
        },
        37: {
            '__info__': 'Keyboard key for Left Arrow.',
            'value': '←'
        },
        38: {
            '__info__': 'Keyboard key for Up Arrow.',
            'value': '↑'
        },
        39: {
            '__info__': 'Keyboard key for Right Arrow.',
            'value': '→'
        },
        40: {
            '__info__': 'Keyboard key for Down Arrow.',
            'value': '↓'
        },
        44: {
            '__info__': 'Keyboard key for Print Screen.',
            'value': 'Print\nScreen'
        },
        45: {
            '__info__': 'Keyboard key for Insert.',
            'value': 'Insert'
        },
        46: {
            '__info__': 'Keyboard key for Delete.',
            'value': 'Delete'
        },
        48: {
            '__info__': 'Keyboard key for 0.',
            'value': '0'
        },
        49: {
            '__info__': 'Keyboard key for 1.',
            'value': '1'
        },
        50: {
            '__info__': 'Keyboard key for 2.',
            'value': '2'
        },
        51: {
            '__info__': 'Keyboard key for 3.',
            'value': '3'
        },
        52: {
            '__info__': 'Keyboard key for 4.',
            'value': '4'
        },
        53: {
            '__info__': 'Keyboard key for 5.',
            'value': '5'
        },
        54: {
            '__info__': 'Keyboard key for 6.',
            'value': '6'
        },
        55: {
            '__info__': 'Keyboard key for 7.',
            'value': '7'
        },
        56: {
            '__info__': 'Keyboard key for 8.',
            'value': '8'
        },
        57: {
            '__info__': 'Keyboard key for 9.',
            'value': '9'
        },
        65: {
            '__info__': 'Keyboard key for A.',
            'value': 'A'
        },
        66: {
            '__info__': 'Keyboard key for B.',
            'value': 'B'
        },
        67: {
            '__info__': 'Keyboard key for C.',
            'value': 'C'
        },
        68: {
            '__info__': 'Keyboard key for D.',
            'value': 'D'
        },
        69: {
            '__info__': 'Keyboard key for E.',
            'value': 'E'
        },
        70: {
            '__info__': 'Keyboard key for F.',
            'value': 'F'
        },
        71: {
            '__info__': 'Keyboard key for G.',
            'value': 'G'
        },
        72: {
            '__info__': 'Keyboard key for H.',
            'value': 'H'
        },
        73: {
            '__info__': 'Keyboard key for I.',
            'value': 'I'
        },
        74: {
            '__info__': 'Keyboard key for J.',
            'value': 'J'
        },
        75: {
            '__info__': 'Keyboard key for K.',
            'value': 'K'
        },
        76: {
            '__info__': 'Keyboard key for L.',
            'value': 'L'
        },
        77: {
            '__info__': 'Keyboard key for M.',
            'value': 'M'
        },
        78: {
            '__info__': 'Keyboard key for N.',
            'value': 'N'
        },
        79: {
            '__info__': 'Keyboard key for O.',
            'value': 'O'
        },
        80: {
            '__info__': 'Keyboard key for P.',
            'value': 'P'
        },
        81: {
            '__info__': 'Keyboard key for Q.',
            'value': 'Q'
        },
        82: {
            '__info__': 'Keyboard key for R.',
            'value': 'R'
        },
        83: {
            '__info__': 'Keyboard key for S.',
            'value': 'S'
        },
        84: {
            '__info__': 'Keyboard key for T.',
            'value': 'T'
        },
        85: {
            '__info__': 'Keyboard key for U.',
            'value': 'U'
        },
        86: {
            '__info__': 'Keyboard key for V.',
            'value': 'V'
        },
        87: {
            '__info__': 'Keyboard key for W.',
            'value': 'W'
        },
        88: {
            '__info__': 'Keyboard key for X.',
            'value': 'X'
        },
        89: {
            '__info__': 'Keyboard key for Y.',
            'value': 'Y'
        },
        90: {
            '__info__': 'Keyboard key for Z.',
            'value': 'Z'
        },
        91: {
            '__info__': 'Keyboard key for Left Windows/Super.',
        },
        92: {
            '__info__': 'Keyboard key for Right Windows/Super.',
        },
        93: {
            '__info__': 'Keyboard key for Menu.',
            'value': 'Menu'
        },
        96: {
            '__info__': 'Keyboard key for Numpad 0.',
            'value': '0\nIns'
        },
        97: {
            '__info__': 'Keyboard key for Numpad 1.',
            'value': '1\nEnd'
        },
        98: {
            '__info__': 'Keyboard key for Numpad 2.',
            'value': '2\n↓'
        },
        99: {
            '__info__': 'Keyboard key for Numpad 3.',
            'value': '3\nPg Dn'
        },
        100: {
            '__info__': 'Keyboard key for Numpad 4.',
            'value': '4\n←'
        },
        101: {
            '__info__': 'Keyboard key for Numpad 5.',
            'value': '5'
        },
        102: {
            '__info__': 'Keyboard key for Numpad 6.',
            'value': '6\n→'
        },
        103: {
            '__info__': 'Keyboard key for Numpad 7.',
            'value': '7\nHome'
        },
        104: {
            '__info__': 'Keyboard key for Numpad 8.',
            'value': '8\n↑'
        },
        105: {
            '__info__': 'Keyboard key for Numpad 9.',
            'value': '9\nPg Up'
        },
        106: {
            '__info__': 'Keyboard key for Multiply.',
            'value': '*'
        },
        107: {
            '__info__': 'Keyboard key for Add.',
            'value': '+'
        },
        109: {
            '__info__': 'Keyboard key for Subtract.',
            'value': '-'
        },
        110: {
            '__info__': 'Keyboard key for Decimal.',
            'value': '-'
        },
        111: {
            '__info__': 'Keyboard key for Divide.',
            'value': '/'
        },
        112: {
            '__info__': 'Keyboard key for F1.',
            'value': 'F1'
        },
        113: {
            '__info__': 'Keyboard key for F2.',
            'value': 'F2'
        },
        114: {
            '__info__': 'Keyboard key for F3.',
            'value': 'F3'
        },
        115: {
            '__info__': 'Keyboard key for F4.',
            'value': 'F4'
        },
        116: {
            '__info__': 'Keyboard key for F5.',
            'value': 'F5'
        },
        117: {
            '__info__': 'Keyboard key for F6.',
            'value': 'F6'
        },
        118: {
            '__info__': 'Keyboard key for F7.',
            'value': 'F7'
        },
        119: {
            '__info__': 'Keyboard key for F8.',
            'value': 'F8'
        },
        120: {
            '__info__': 'Keyboard key for F9.',
            'value': 'F9'
        },
        121: {
            '__info__': 'Keyboard key for F10.',
            'value': 'F10'
        },
        122: {
            '__info__': 'Keyboard key for F11.',
            'value': 'F11'
        },
        123: {
            '__info__': 'Keyboard key for F12.',
            'value': 'F12'
        },
        144: {
            '__info__': 'Keyboard key for Number Lock.',
            'value': 'Num\nLock'
        },
        145: {
            '__info__': 'Keyboard key for Scroll Lock.',
            'value': 'Scroll\nLock'
        },
        160: {
            '__info__': 'Keyboard key for Left Shift.',
            'value': 'Shift'
        },
        161: {
            '__info__': 'Keyboard key for Right Shift.',
            'value': 'Shift'
        },
        162: {
            '__info__': 'Keyboard key for Left Control.',
            'value': 'Ctrl'
        },
        163: {
            '__info__': 'Keyboard key for Right Control.',
            'value': 'Ctrl'
        },
        164: {
            '__info__': 'Keyboard key for Left Alt.',
            'value': 'Alt'
        },
        165: {
            '__info__': 'Keyboard key for Right Alt.',
            'value': 'Alt Gr'
        },
        186: {
            '__info__': 'Keyboard key for Colon.',
            'value': ':\n;'
        },
        187: {
            '__info__': 'Keyboard key for Equals.',
            'value': '+\n='
        },
        188: {
            '__info__': 'Keyboard key for Comma.',
            'value': '<\n,'
        },
        189: {
            '__info__': 'Keyboard key for Hyphen/Dash.',
            'value': '_\n-'
        },
        190: {
            '__info__': 'Keyboard key for Period.',
            'value': '>\n.'
        },
        191: {
            '__info__': 'Keyboard key for Forward Slash.',
            'value': '?\n/'
        },
        192: {
            '__info__': 'Keyboard key for Apostophie.',
            'value': '@\n\''
        },
        219: {
            '__info__': 'Keyboard key for Left Square Bracket.',
            'value': '{\n['
        },
        220: {
            '__info__': 'Keyboard key for Back Slash.',
            'value': '|\n\\'
        },
        221: {
            '__info__': 'Keyboard key for Right Square Bracket.',
            'value': '}\n]'
        },
        222: {
            '__info__': 'Keyboard key for Hashtag/Number Sign.',
            'value': '~\n#'
        },
        223: {
            '__info__': 'Keyboard key for Tilde.',
            'value': '¦\n`'
        },
    }
}

PATH_DEFAULT = {
    'Links': {
        '__priority__': 1,
        'Strings': {
            '__info__': 'Which base language to use.',
            'value': 'en_GB',
            'type': str
        },
        'Keyboard': {
            '__info__': 'Which language to use for the keyboard layout.',
            'value': 'en_US',
            'type': str
        }
    },
    'Inherit': {
        '__priority__': 2,
        'Strings': {
            '__info__': 'Which language to inherit from. Optional, but lets you reuse strings defined in other files if your language is similar.',
            'allow_empty': True,
            'type': str
        }
    }
}


def get_language_paths(*languages):
    """Get the paths given for strings and keyboard from current language."""
    path_default = {'Links': {'Strings': 'en_GB', 'Keyboard': 'en_US'},
                    'Inherit': {'Strings': {'allow_empty': True}}}

    language_paths = [os.path.join(LANGUAGE_BASE_PATH, language + '.ini') for language in languages][::-1]
    paths = Config(PATH_DEFAULT, editable_dict=True).load(*language_paths)

    #Edit the links to use the language folder
    paths['NewLinks'] = {}
    paths['NewLinks']['Strings'] = os.path.join(LANGUAGE_BASE_PATH, STRINGS_FOLDER, paths['Links']['Strings'] + '.ini')
    if paths['Inherit']['Strings']:
        paths['NewLinks']['StringsBackup'] = os.path.join(LANGUAGE_BASE_PATH, STRINGS_FOLDER, paths['Inherit']['Strings'] + '.ini')
    paths['NewLinks']['StringsBase'] = os.path.join(LANGUAGE_BASE_PATH, STRINGS_FOLDER, DEFAULT_LANGUAGE + '.ini')
    #TODO: Use new keyboard folder
    paths['NewLinks']['Keyboard'] = os.path.join(LANGUAGE_BASE_PATH, KEYBOARD_LAYOUT_FOLDER, paths['Links']['Keyboard'] + '.txt')
    
    return paths


class Language(object):
    def __init__(self, local_language=None):
        self.local_language = local_language or CONFIG['Main']['Language']
        self.reload()
    
    def reload(self, local_language=None):
        self.paths = get_language_paths(local_language or CONFIG['Main']['Language'], DEFAULT_LANGUAGE)
        self.strings = self._strings()

    def _strings(self):
        strings = Config(LANGUAGE_DEFAULTS, default_settings={'type': str, 'allow_empty': True})
        strings.load(self.paths['NewLinks']['Strings'], self.paths['NewLinks'].get('StringsBackup', None), self.paths['NewLinks']['StringsBase'])
        return strings

    def keyboard_old(self, extended=True):
        keyboard_layout = []

        #Read lines from file
        try:
            with codecs.open(self.paths['NewLinks']['Keyboard'], 'r', 'utf-8') as f:
                read_data = f.read()
                if ord(read_data[0]) == 65279: #Remove dumb utf-8 marker that won't disappear
                    read_data = read_data[1:]
                data = read_data.strip().splitlines()
        except IOError:
            data = []
            
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
                
                keyboard_layout[-1].append((name, width, height))
                
        return keyboard_layout

LANGUAGE = Language()