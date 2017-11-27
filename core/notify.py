"""
This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""

from __future__ import absolute_import

from core.base import format_file_path
from core.config import CONFIG
from core.constants import DEFAULT_NAME, DEFAULT_PATH
from core.language import Language
from core.os import get_documents_path


MESSAGE_DEBUG = -1

MOUSE_UNDETECTED = 0

MOUSE_DETECTED = 1

MOUSE_POSITION = 2

MOUSE_OFFSCREEN = 3

MOUSE_ONSCREEN = 4

MOUSE_CLICKED = 8

MOUSE_UNCLICKED = 9

MOUSE_CLICKED_OFFSCREEN = 10

MOUSE_CLICKED_HELD = 11

MOUSE_CLICKED_DOUBLE = 13

TRACK_COMPRESS_START = 14

TRACK_COMPRESS_END = 15

RESOLUTION_CHANGED = 16

MONITOR_CHANGED = 17

APPLICATION_RESOLUTION = 18

APPLICATION_MOVE = 19

APPLICATION_RESIZE = 20

KEYBOARD_PRESSES = 32

KEYBOARD_PRESSES_HELD = 33

KEYBOARD_RELEASED = 34

APPLICATION_STARTED = 48

APPLICATION_QUIT = 49

APPLICATION_RELOAD = 50

APPLICATION_LISTEN = 51

APPLICATION_LOADING = 52

APPLICATION_FOCUSED = 53

APPLICATION_UNFOCUSED = 54

APPLIST_UPDATE_START = 55

APPLIST_UPDATE_SUCCESS = 56

APPLIST_UPDATE_FAIL = 57

SAVE_START = 64

SAVE_SUCCESS = 65

SAVE_FAIL = 66

SAVE_FAIL_RETRY = 67

SAVE_FAIL_END = 68

SAVE_SKIP = 69

SAVE_PREPARE = 70

START_MAIN = 80

START_THREAD = 81

DATA_LOADED = 82

DATA_NOTFOUND = 83

MT_PATH = 84

QUEUE_SIZE = 96

PROCESS_EXIT = 112

THREAD_EXIT = 113

PROCESS_NOT_UNIQUE = 114

GAMEPAD_REFRESH = 128

GAMEPAD_AXIS = 129

GAMEPAD_BUTTON_PRESS = 130

GAMEPAD_BUTTON_HELD = 131

GAMEPAD_BUTTON_RELEASED = 132

GAMEPAD_FOUND = 133

GAMEPAD_LOST = 134


def get_plural(word, amount):
    return word['single'] if amount == 1 else word['plural']


def capitalize(sentence):
    try:
        return sentence[0].upper() + sentence[1:]
    except IndexError:
        return ''
    
    
class Notify(object):
    
    def __init__(self):
        all_strings = Language().get_strings()
        self.string = all_strings['string']['track']
        self.word = all_strings['word']
        
        self.reset()
    
    def debug(self, *args):
        return self.__call__(MESSAGE_DEBUG, *args)
    
    def _mb(self, id):
        mb = self.word['mousebutton']
        return (mb['left'], mb['middle'], mb['right'])[id]
    
    def __call__(self, message_id, *args):
        
        q0 = self.message_queue[0].append
        q1 = self.message_queue[1].append
        q2 = self.message_queue[2].append
        
        if message_id == MESSAGE_DEBUG:
            self._debug.append(args)
            
        elif message_id == MOUSE_UNDETECTED:
            q2(self.string['mouse']['undetected'])
            
        elif message_id == MOUSE_DETECTED:
            q2(self.string['mouse']['detected'])
            
        elif message_id == MOUSE_OFFSCREEN:
            q1(self.string['mouse']['offscreen'])
            
        elif message_id == MOUSE_ONSCREEN:
            q1(self.string['mouse']['onscreen'])
            
        elif message_id == MOUSE_POSITION:
            q0(self.string['mouse']['position'].format(X=args[0][0], Y=args[0][1]))
        
        #Mouse clicks
        elif message_id in (MOUSE_CLICKED, MOUSE_CLICKED_DOUBLE, MOUSE_CLICKED_HELD):
            if message_id == MOUSE_CLICKED:
                click_group = 'clicked'
                click_type = 'single'
            elif message_id == MOUSE_CLICKED_DOUBLE:
                click_group = 'clicked'
                click_type = 'double'
            elif message_id == MOUSE_CLICKED_HELD:
                click_group = 'held'
                click_type = 'single'
            
            mouse_button = args[0]
            try:
                resolution = args[1]
            except IndexError:
                screen = 'offscreen'
                resolution = (0, 0)
            else:
                screen = 'onscreen'
                
            q1(self.string['mouse'][click_group][screen].format(MB=self._mb(mouse_button),
                                                                X=resolution[0], Y=resolution[1],
                                                                C=self.word['mouse']['click'][click_type]))
        
        elif message_id == MOUSE_UNCLICKED:
            q0(self.string['mouse']['unclicked'])
            
        elif message_id == TRACK_COMPRESS_START:
            q2(self.string['compress']['start'])
            
        elif message_id == TRACK_COMPRESS_END:
            q2(self.string['compress']['end'])
            
        elif message_id == RESOLUTION_CHANGED:
            q2(self.string['resolution']['new'].format(X1=args[0][0], Y1=args[0][1],
                                                       X2=args[1][0], Y2=args[1][1]))
                                                   
        elif message_id == MONITOR_CHANGED:
            q1(self.string['resolution']['changed'].format(X1=args[0][0], Y1=args[0][1],
                                                           X2=args[1][0], Y2=args[1][1]))
                                                       
        elif message_id == APPLICATION_RESOLUTION:
            q1(self.string['resolution']['application']['start'].format(X=args[0][0], Y=args[0][1]))
                                                       
        elif message_id == APPLICATION_MOVE:
            q1(self.string['resolution']['application']['move'].format(X1=args[0][0], Y1=args[0][1],
                                                                       X2=args[1][0], Y2=args[1][1]))
                                                       
        elif message_id == APPLICATION_RESIZE:
            q1(self.string['resolution']['application']['resize'].format(X1=args[0][0], Y1=args[0][1],
                                                                         X2=args[1][0], Y2=args[1][1]))
        
        #Key presses
        elif message_id in (KEYBOARD_PRESSES, KEYBOARD_PRESSES_HELD, KEYBOARD_RELEASED):
            keypresses = args
            num_presses = len(keypresses)
            key = get_plural(self.word['key'], num_presses)
            press = get_plural(self.word['press'], num_presses)
            release = get_plural(self.word['release'], num_presses)
            
            if message_id == KEYBOARD_PRESSES:
                q1(self.string['keyboard']['press'].format(K=key, P=press, V=', '.join(keypresses)))
                
            elif message_id == KEYBOARD_PRESSES_HELD:
                q1(self.string['keyboard']['held'].format(K=key, P=press, V=', '.join(keypresses)))
                
            elif message_id == KEYBOARD_RELEASED:
                q0(self.string['keyboard']['release'].format(K=key, R=release, V=', '.join(keypresses)))
        
        elif message_id == GAMEPAD_REFRESH:
            q0(self.string['gamepad']['refresh'])
            
        elif message_id == GAMEPAD_AXIS:
            gamepad_id, axis, value = args
            q0(self.string['gamepad']['axis'].format(N=gamepad_id, A=axis, V=value))
        
        #Gamepad button presses
        elif message_id in (GAMEPAD_BUTTON_PRESS, GAMEPAD_BUTTON_HELD, GAMEPAD_BUTTON_RELEASED):
            gamepad_number, buttons_ids = args
            num_buttons = len(buttons_ids)
            button = get_plural(self.word['button'], num_buttons)
            press = get_plural(self.word['press'], num_buttons)
            release = get_plural(self.word['release'], num_buttons)
            
            buttons = [str(id) for id in buttons_ids] #TODO: set button names
            
            if message_id == GAMEPAD_BUTTON_PRESS:
                q1(self.string['gamepad']['button']['press'].format(N=gamepad_number, B=button, V=', '.join(buttons), P=press))
            
            elif message_id == GAMEPAD_BUTTON_HELD:
                q1(self.string['gamepad']['button']['held'].format(N=gamepad_number, B=button, V=', '.join(buttons), P=press))
            
            elif message_id == GAMEPAD_BUTTON_RELEASED:
                q0(self.string['gamepad']['button']['release'].format(N=gamepad_number, B=button, V=', '.join(buttons), R=release))
        
        elif message_id == GAMEPAD_FOUND:
            gamepad_number = args[0]
            q2(self.string['gamepad']['found'].format(N=gamepad_number))
            
        elif message_id == GAMEPAD_LOST:
            gamepad_number = args[0]
            q2(self.string['gamepad']['lost'].format(N=gamepad_number))
            
        elif message_id == APPLICATION_STARTED:
            q2(self.string['application']['start'].format(A=args[0][0]))
        
        #Application changes
        elif message_id in (APPLICATION_LOADING, APPLICATION_QUIT, APPLICATION_FOCUSED, APPLICATION_UNFOCUSED):
            try:
                application = args[0][0]
                if application is None:
                    raise TypeError()
            except (IndexError, TypeError):
                application = DEFAULT_NAME
            
            if message_id == APPLICATION_LOADING:
                q2(self.string['application']['load'].format(A=application))
                
            if message_id == APPLICATION_QUIT:
                q2(self.string['application']['quit'].format(A=application))
            
            if message_id == APPLICATION_FOCUSED:
                q1(self.string['application']['focused'].format(A=application))
            
            if message_id == APPLICATION_UNFOCUSED:
                q1(self.string['application']['unfocused'].format(A=application))
            
            
        elif message_id == APPLICATION_RELOAD:
            q1(self.string['application']['reload'])
            
        elif message_id == APPLICATION_LISTEN:
            q1(self.string['application']['listen'])
            
        elif message_id == APPLIST_UPDATE_START:
            q1(self.string['application']['update']['start'])
            
        elif message_id == APPLIST_UPDATE_SUCCESS:
            q1(self.string['application']['update']['success'])
            
        elif message_id == APPLIST_UPDATE_FAIL:
            q1(self.string['application']['update']['fail'])
            
        elif message_id == SAVE_START:
            q2(self.string['save']['start'])
            
        elif message_id == SAVE_SUCCESS:
            q2(self.string['save']['success'])
            
        elif message_id == SAVE_FAIL:
            q2(self.string['save']['fail']['noretry'])
            
        elif message_id == SAVE_FAIL_RETRY:
            second = get_plural(self.word['second'], args[0])
            q2(self.string['save']['fail']['retry'].format(T=args[0], S=second, C=args[1] + 1, M=args[2]))
            
        elif message_id == SAVE_FAIL_END:
            q2(self.string['save']['fail']['end'])
            
        elif message_id == SAVE_SKIP:
            save_frequency, queue_size = args
            if queue_size > 2:
                q2(self.string['save']['skip']['nochange'])
            else:
                second = get_plural(self.word['second'], args[0])
                q2(self.string['save']['skip']['inactive'].format(T=save_frequency, S=second))
                
        elif message_id == SAVE_PREPARE:
            q2(self.string['save']['prepare'])
            
        elif message_id == START_MAIN:
            q2(self.string['script']['main']['start'])
            
        elif message_id == START_THREAD:
            q2(self.string['script']['thread']['start'])
            
        elif message_id == DATA_LOADED:
            q1(self.string['profile']['load'])
            
        elif message_id == DATA_NOTFOUND:
            q1(self.string['profile']['new'])
            
        elif message_id == MT_PATH:
            q2(self.string['path'].format(P=format_file_path(DEFAULT_PATH)))
            
        elif message_id == QUEUE_SIZE:
            command = get_plural(self.word['command'], args[0])
            q1(self.string['queue'].format(N=args[0], C=command))
            
        elif message_id == PROCESS_EXIT:
            q2(self.string['script']['main']['end'])
            
        elif message_id == THREAD_EXIT:
            q2(self.string['script']['thread']['end'])
            
        elif message_id == PROCESS_NOT_UNIQUE:
            q2(self.string['script']['process']['duplicate'])
        
        return self

    def get_output(self):
        allowed_levels = range(CONFIG['Advanced']['MessageLevel'], 3)
        output = [capitalize(u' | '.join(self.message_queue[i])) for i in allowed_levels][::-1]
        message = u' | '.join(i for i in output if i)
        for msg in self._debug:
            print(u', '.join(map(str, msg)))
                
        self.reset()
        return message

    def send(self, q):
        output = self.get_output()
        if output:
            q.put(output)

    def reset(self):
        self.message_queue = {0: [], 1: [], 2: []}
        self._debug = []

    
NOTIFY = Notify()
NOTIFY_DEBUG = NOTIFY.debug