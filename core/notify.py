"""
This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""

from __future__ import absolute_import

from core.base import format_file_path
from core.compatibility import Message
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

SERVER_SOCKET_START = 144

SERVER_SOCKET_PORT = 145

SERVER_SOCKET_CONNECT = 146

SERVER_SOCKET_WAIT = 147

SERVER_WEB_START = 148

SERVER_WEB_PORT = 149

SERVER_PORT_NEW = 150

SERVER_PORT_TAKEN = 151

SERVER_PORT_CLOSE = 152

SERVER_SECRET_SET = 153

SERVER_SECRET_SUCCESS = 154

SERVER_SECRET_FAIL = 155

IMPORT_FAILED = 160

TRACKING_RESUME = 176

TRACKING_PAUSE = 177

TRACKING_TERMINATE = 178

TRACKING_RESTART = 179

URL_REQUEST = 192


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
        self.strings = all_strings['string']
        self.word = all_strings['word']
        self._failed_imports = set()
        
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
        s = self.strings
        
        if message_id == MESSAGE_DEBUG:
            self._debug.append(args)
            
        elif message_id == MOUSE_UNDETECTED:
            q2(s['track']['mouse']['undetected'])
            
        elif message_id == MOUSE_DETECTED:
            q2(s['track']['mouse']['detected'])
            
        elif message_id == MOUSE_OFFSCREEN:
            q1(s['track']['mouse']['offscreen'])
            
        elif message_id == MOUSE_ONSCREEN:
            q1(s['track']['mouse']['onscreen'])
            
        elif message_id == MOUSE_POSITION:
            q0(s['track']['mouse']['position'].format(X=args[0][0], Y=args[0][1]))
        
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
                
            q1(s['track']['mouse'][click_group][screen].format(MB=self._mb(mouse_button),
                                                               X=resolution[0], Y=resolution[1],
                                                               C=self.word['mouse']['click'][click_type]))
        
        elif message_id == MOUSE_UNCLICKED:
            q0(s['track']['mouse']['unclicked'])
            
        elif message_id == TRACK_COMPRESS_START:
            q2(s['track']['compress']['start'])
            
        elif message_id == TRACK_COMPRESS_END:
            q2(s['track']['compress']['end'])
            
        elif message_id == RESOLUTION_CHANGED:
            q2(s['track']['resolution']['new'].format(X1=args[0][0], Y1=args[0][1],
                                                      X2=args[1][0], Y2=args[1][1]))
                                                   
        elif message_id == MONITOR_CHANGED:
            q1(s['track']['resolution']['changed'].format(X1=args[0][0], Y1=args[0][1],
                                                          X2=args[1][0], Y2=args[1][1]))
                                                       
        elif message_id == APPLICATION_RESOLUTION:
            q1(s['track']['resolution']['application']['start'].format(X=args[0][0], Y=args[0][1]))
                                                       
        elif message_id == APPLICATION_MOVE:
            q1(s['track']['resolution']['application']['move'].format(X1=args[0][0], Y1=args[0][1],
                                                                      X2=args[1][0], Y2=args[1][1]))
                                                       
        elif message_id == APPLICATION_RESIZE:
            q1(s['track']['resolution']['application']['resize'].format(X1=args[0][0], Y1=args[0][1],
                                                                        X2=args[1][0], Y2=args[1][1]))
        
        #Key presses
        elif message_id in (KEYBOARD_PRESSES, KEYBOARD_PRESSES_HELD, KEYBOARD_RELEASED):
            keypresses = args
            num_presses = len(keypresses)
            key = get_plural(self.word['key'], num_presses)
            press = get_plural(self.word['press'], num_presses)
            release = get_plural(self.word['release'], num_presses)
            
            if message_id == KEYBOARD_PRESSES:
                q1(s['track']['keyboard']['press'].format(K=key, P=press, V=', '.join(keypresses)))
                
            elif message_id == KEYBOARD_PRESSES_HELD:
                q1(s['track']['keyboard']['held'].format(K=key, P=press, V=', '.join(keypresses)))
                
            elif message_id == KEYBOARD_RELEASED:
                q0(s['track']['keyboard']['release'].format(K=key, R=release, V=', '.join(keypresses)))
        
        elif message_id == GAMEPAD_REFRESH:
            q0(s['track']['gamepad']['refresh'])
            
        elif message_id == GAMEPAD_AXIS:
            gamepad_id, axis, value = args
            q0(s['track']['gamepad']['axis'].format(N=gamepad_id, A=axis, V=value))
        
        #Gamepad button presses
        elif message_id in (GAMEPAD_BUTTON_PRESS, GAMEPAD_BUTTON_HELD, GAMEPAD_BUTTON_RELEASED):
            gamepad_number, buttons_ids = args
            num_buttons = len(buttons_ids)
            button = get_plural(self.word['button'], num_buttons)
            press = get_plural(self.word['press'], num_buttons)
            release = get_plural(self.word['release'], num_buttons)
            
            buttons = [str(id) for id in buttons_ids] #TODO: set button names
            
            if message_id == GAMEPAD_BUTTON_PRESS:
                q1(s['track']['gamepad']['button']['press'].format(N=gamepad_number, B=button, V=', '.join(buttons), P=press))
            
            elif message_id == GAMEPAD_BUTTON_HELD:
                q1(s['track']['gamepad']['button']['held'].format(N=gamepad_number, B=button, V=', '.join(buttons), P=press))
            
            elif message_id == GAMEPAD_BUTTON_RELEASED:
                q0(s['track']['gamepad']['button']['release'].format(N=gamepad_number, B=button, V=', '.join(buttons), R=release))
        
        elif message_id == GAMEPAD_FOUND:
            gamepad_number = args[0]
            q2(s['track']['gamepad']['found'].format(N=gamepad_number))
            
        elif message_id == GAMEPAD_LOST:
            gamepad_number = args[0]
            q2(s['track']['gamepad']['lost'].format(N=gamepad_number))
            
        elif message_id == APPLICATION_STARTED:
            q2(s['track']['application']['start'].format(A=args[0][0]))
        
        #Application changes
        elif message_id in (APPLICATION_LOADING, APPLICATION_QUIT, APPLICATION_FOCUSED, APPLICATION_UNFOCUSED):
            try:
                application = args[0][0]
                if application is None:
                    raise TypeError()
            except (IndexError, TypeError):
                application = DEFAULT_NAME
            
            if message_id == APPLICATION_LOADING:
                q2(s['track']['application']['load'].format(A=application))
                
            if message_id == APPLICATION_QUIT:
                q2(s['track']['application']['quit'].format(A=application))
            
            if message_id == APPLICATION_FOCUSED:
                q1(s['track']['application']['focused'].format(A=application))
            
            if message_id == APPLICATION_UNFOCUSED:
                q1(s['track']['application']['unfocused'].format(A=application))
            
            
        elif message_id == APPLICATION_RELOAD:
            q1(s['track']['application']['reload'])
            
        elif message_id == APPLICATION_LISTEN:
            q1(s['track']['application']['listen'])
            
        elif message_id == APPLIST_UPDATE_START:
            q1(s['track']['application']['update']['start'])
            
        elif message_id == APPLIST_UPDATE_SUCCESS:
            q1(s['track']['application']['update']['success'])
            
        elif message_id == APPLIST_UPDATE_FAIL:
            q1(s['track']['application']['update']['fail'])
            
        elif message_id == SAVE_START:
            q2(s['track']['save']['start'])
            
        elif message_id == SAVE_SUCCESS:
            q2(s['track']['save']['success'])
            
        elif message_id == SAVE_FAIL:
            q2(s['track']['save']['fail']['noretry'])
            
        elif message_id == SAVE_FAIL_RETRY:
            second = get_plural(self.word['second'], args[0])
            q2(s['track']['save']['fail']['retry'].format(T=args[0], S=second, C=args[1] + 1, M=args[2]))
            
        elif message_id == SAVE_FAIL_END:
            q2(s['track']['save']['fail']['end'])
            
        elif message_id == SAVE_SKIP:
            save_frequency, queue_size = args
            if queue_size > 2:
                q2(s['track']['save']['skip']['nochange'])
            else:
                second = get_plural(self.word['second'], args[0])
                q2(s['track']['save']['skip']['inactive'].format(T=save_frequency, S=second))
                
        elif message_id == SAVE_PREPARE:
            q2(s['track']['save']['prepare'])
            
        elif message_id == START_MAIN:
            q2(s['track']['script']['main']['start'])
            
        elif message_id == START_THREAD:
            q2(s['track']['script']['thread']['start'])
            
        elif message_id == DATA_LOADED:
            q1(s['track']['profile']['load'])
            
        elif message_id == DATA_NOTFOUND:
            q1(s['track']['profile']['new'])
            
        elif message_id == MT_PATH:
            q2(s['track']['path'].format(P=format_file_path(DEFAULT_PATH)))
            
        elif message_id == QUEUE_SIZE:
            command = get_plural(self.word['command'], args[0])
            q1(s['track']['queue'].format(N=args[0], C=command))
            
        elif message_id == PROCESS_EXIT:
            q2(s['track']['script']['main']['end'])
            
        elif message_id == THREAD_EXIT:
            q2(s['track']['script']['thread']['end'])
            
        elif message_id == PROCESS_NOT_UNIQUE:
            q2(s['track']['script']['process']['duplicate'])
            
        elif message_id == SERVER_SOCKET_START:
            q2(s['server']['socket']['start'])
            
        elif message_id == SERVER_WEB_START:
            q2(s['server']['web']['start'])
            
        elif message_id == SERVER_SOCKET_PORT:
            q2(s['server']['socket']['port'].format(P=args[0]))
            
        elif message_id == SERVER_WEB_PORT:
            q2(s['server']['web']['port'].format(P=args[0]))
            
        elif message_id == SERVER_SOCKET_CONNECT:
            q2(s['server']['socket']['client']['connect'].format(H=args[0], P=args[1]))
            
        elif message_id == SERVER_SOCKET_WAIT:
            q0(s['server']['socket']['client']['wait'])
            
        elif message_id == SERVER_PORT_NEW:
            q1(s['server']['port']['new'])
            
        elif message_id == SERVER_PORT_TAKEN:
            q1(s['server']['port']['taken'].format(P=args[0]))
            
        elif message_id == SERVER_PORT_CLOSE:
            q1(s['server']['port']['close'])
            
        elif message_id == SERVER_SECRET_SET:
            q1(s['server']['socket']['secret']['set'].format(S=args[0]))
            
        elif message_id == SERVER_SECRET_SUCCESS:
            q1(s['server']['socket']['secret']['success'])
            
        elif message_id == SERVER_SECRET_FAIL:
            q1(s['server']['socket']['secret']['fail'])
            
        elif message_id == IMPORT_FAILED:
            if args[0] not in self._failed_imports:
                self._failed_imports.add(args[0])
                if len(args) > 1:
                    q2('Import of "{}" failed. Reason: "{}".'.format(args[0], args[1]))
                else:
                    q2('Import of "{}" failed.'.format(args[0]))
            
        elif message_id == TRACKING_RESUME:
            q2(s['server']['status']['resume'])
            
        elif message_id == TRACKING_PAUSE:
            q2(s['server']['status']['pause'])
            
        elif message_id == TRACKING_TERMINATE:
            q2(s['server']['status']['stop'])
            
        elif message_id == TRACKING_RESTART:
            q2(s['server']['status']['restart'])
            
        elif message_id == URL_REQUEST:
            q0(s['url']['request'].format(U=args[0]))
        
        return self

    def get_output(self):
        allowed_levels = range(CONFIG['Advanced']['MessageLevel'], 3)
        output = [capitalize(u' | '.join(self.message_queue[i])) for i in allowed_levels][::-1]
        message = u' | '.join(i for i in output if i)
        for msg in self._debug:
            Message(msg)
        
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