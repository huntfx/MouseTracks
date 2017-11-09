from __future__ import absolute_import

from core.config import CONFIG
from core.constants import DEFAULT_NAME, DEFAULT_PATH, format_file_path
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
            self.debug.append(args)
            
        if message_id == MOUSE_UNDETECTED:
            q2(self.string['mouse']['undetected'])
            
        if message_id == MOUSE_DETECTED:
            q2(self.string['mouse']['detected'])
            
        if message_id == MOUSE_OFFSCREEN:
            q1(self.string['mouse']['offscreen'])
            
        if message_id == MOUSE_ONSCREEN:
            q1(self.string['mouse']['onscreen'])
            
        if message_id == MOUSE_POSITION:
            q0(self.string['mouse']['position'].format(X=args[0][0], Y=args[0][1]))
            
        if message_id == MOUSE_CLICKED:
            mouse_button = args[0]
            try:
                resolution = args[1]
            except IndexError:
                q1(self.string['mouse']['clicked']['offscreen'].format(MB=self._mb(mouse_button),
                                                                       C=self.word['mouse']['click']['single']))
            else:
                q1(self.string['mouse']['clicked']['onscreen'].format(MB=self._mb(mouse_button),
                                                                      X=resolution[0], Y=resolution[1],
                                                                      C=self.word['mouse']['click']['single']))
            
        if message_id == MOUSE_CLICKED_DOUBLE:
            mouse_button = args[0]
            try:
                resolution = args[1]
            except IndexError:
                q1(self.string['mouse']['clicked']['offscreen'].format(MB=self._mb(mouse_button),
                                                                       C=self.word['mouse']['click']['double']))
            else:
                q1(self.string['mouse']['clicked']['onscreen'].format(MB=self._mb(mouse_button),
                                                                      X=resolution[0], Y=resolution[1],
                                                                      C=self.word['mouse']['click']['double']))
            
        if message_id == MOUSE_CLICKED_HELD:
            mouse_button = args[0]
            try:
                resolution = args[1]
            except IndexError:
                q1(self.string['mouse']['held']['offscreen'].format(MB=self._mb(mouse_button)))
            else:
                q1(self.string['mouse']['held']['onscreen'].format(MB=self._mb(mouse_button),
                                                                      X=resolution[0], Y=resolution[1]))
                                                                      
        if message_id == MOUSE_UNCLICKED:
            q0(self.string['mouse']['unclicked'])
            
        if message_id == TRACK_COMPRESS_START:
            q2(self.string['compress']['start'])
            
        if message_id == TRACK_COMPRESS_END:
            q2(self.string['compress']['end'])
            
        if message_id == RESOLUTION_CHANGED:
            q2(self.string['resolution']['new'].format(X1=args[0][0], Y1=args[0][1],
                                                       X2=args[1][0], Y2=args[1][1]))
                                                   
        if message_id == MONITOR_CHANGED:
            q1(self.string['resolution']['changed'].format(X1=args[0][0], Y1=args[0][1],
                                                           X2=args[1][0], Y2=args[1][1]))
                                                       
        if message_id == APPLICATION_RESOLUTION:
            q1(self.string['resolution']['application']['start'].format(X=args[0][0], Y=args[0][1]))
                                                       
        if message_id == APPLICATION_MOVE:
            q1(self.string['resolution']['application']['move'].format(X1=args[0][0], Y1=args[0][1],
                                                                       X2=args[1][0], Y2=args[1][1]))
                                                       
        if message_id == APPLICATION_RESIZE:
            q1(self.string['resolution']['application']['resize'].format(X1=args[0][0], Y1=args[0][1],
                                                                         X2=args[1][0], Y2=args[1][1]))
        
        if message_id == KEYBOARD_PRESSES:
            _press = self.word['keypress']
            press = _press['single'] if len(args[0]) == 1 else _press['plural']
            q1(self.string['keyboard']['press'].format(K=', '.join(*args), P=press))
            
        if message_id == KEYBOARD_PRESSES_HELD:
            _press = self.word['keypress']
            press = _press['single'] if len(args[0]) == 1 else _press['plural']
            q1(self.string['keyboard']['held'].format(K=', '.join(*args), P=press))
            
        if message_id == APPLICATION_STARTED:
            q2(self.string['application']['start'].format(A=args[0][0]))
            
        if message_id == APPLICATION_LOADING:
            try:
                if args[0][0] is None:
                    raise TypeError()
            except (IndexError, TypeError):
                profile = DEFAULT_NAME
            else:
                profile = args[0][0]
            q2(self.string['application']['load'].format(A=profile))
            
        if message_id == APPLICATION_QUIT:
            try:
                if args[0][0] is None:
                    raise TypeError()
            except (IndexError, TypeError):
                profile = DEFAULT_NAME
            else:
                profile = args[0][0]
            q2(self.string['application']['quit'].format(A=profile))
            
        if message_id == APPLICATION_RELOAD:
            q1(self.string['application']['reload'])
            
        if message_id == APPLICATION_LISTEN:
            q1(self.string['application']['listen'])
            
        if message_id == APPLICATION_FOCUSED:
            try:
                if args[0][0] is None:
                    raise TypeError()
            except (IndexError, TypeError):
                profile = DEFAULT_NAME
            else:
                profile = args[0][0]
            q1(self.string['application']['focused'].format(A=profile))
            
        if message_id == APPLICATION_UNFOCUSED:
            try:
                if args[0][0] is None:
                    raise TypeError()
            except (IndexError, TypeError):
                profile = DEFAULT_NAME
            else:
                profile = args[0][0]
            q1(self.string['application']['unfocused'].format(A=profile))
            
        if message_id == APPLIST_UPDATE_START:
            q1(self.string['application']['update']['start'])
            
        if message_id == APPLIST_UPDATE_SUCCESS:
            q1(self.string['application']['update']['success'])
            
        if message_id == APPLIST_UPDATE_FAIL:
            q1(self.string['application']['update']['fail'])
            
        if message_id == SAVE_START:
            q2(self.string['save']['start'])
            
        if message_id == SAVE_SUCCESS:
            q2(self.string['save']['success'])
            
        if message_id == SAVE_FAIL:
            q2(self.string['save']['fail']['noretry'])
            
        if message_id == SAVE_FAIL_RETRY:
            _second = self.word['second']
            second = _second['single'] if args[0] == 1 else _second['plural']
            q2(self.string['save']['fail']['retry'].format(T=args[0], S=second, C=args[1] + 1, M=args[2]))
            
        if message_id == SAVE_FAIL_END:
                q2(self.string['save']['fail']['end'])
        if message_id == SAVE_SKIP:
            if args[1] > 2:
                q2(self.string['save']['skip']['nochange'])
            else:
                _second = self.word['second']
                second = _second['single'] if args[0] == 1 else _second['plural']
                q2(self.string['save']['skip']['inactive'].format(T=args[0], S=second))
                
        if message_id == SAVE_PREPARE:
            q2(self.string['save']['prepare'])
            
        if message_id == START_MAIN:
            q2(self.string['script']['main']['start'])
            
        if message_id == START_THREAD:
            q2(self.string['script']['thread']['start'])
            
        if message_id == DATA_LOADED:
            q1(self.string['profile']['load'])
            
        if message_id == DATA_NOTFOUND:
            q1(self.string['profile']['new'])
            
        if message_id == MT_PATH:
            q2(self.string['path'].format(P=format_file_path(DEFAULT_PATH)))
            
        if message_id == QUEUE_SIZE:
            _command = self.word['command']
            command = _command['single'] if args[0] == 1 else _command['plural']
            q1(self.string['queue'].format(N=args[0], C=command))
            
        if message_id == PROCESS_EXIT:
            q2(self.string['script']['main']['end'])
            
        if message_id == THREAD_EXIT:
            q2(self.string['script']['thread']['end'])
            
        if message_id == PROCESS_NOT_UNIQUE:
            q2(self.string['script']['process']['duplicate'])
        
        return self

    def get_output(self):
        allowed_levels = range(CONFIG['Advanced']['MessageLevel'], 3)
        output = [u' | '.join(self.message_queue[i]) for i in allowed_levels][::-1]
        message = u' | '.join(i for i in output if i)
        for msg in self.debug:
            print(u', '.join(map(str, msg)))
                
        self.reset()
        return message

    def send(self, q):
        output = self.get_output()
        if output:
            q.put(output)

    def reset(self):
        self.message_queue = {0: [], 1: [], 2: []}
        self.debug = []

    
NOTIFY = Notify()
NOTIFY_DEBUG = NOTIFY.debug
