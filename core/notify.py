from __future__ import absolute_import

from core.config import CONFIG
from core.constants import DEFAULT_NAME
from core.language import Language

STRINGS = Language().get_strings()
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
MOUSE_HELD = 12
TRACK_COMPRESS_START = 13
TRACK_COMPRESS_END = 14
RESOLUTION_CHANGED = 16
MONITOR_CHANGED = 17
KEYBOARD_PRESSES = 32
KEYBOARD_PRESSES_HELD = 33
APPLICATION_STARTED = 48
APPLICATION_QUIT = 49
APPLICATION_RELOAD = 50
APPLICATION_LISTEN = 51
APPLICATION_LOADING = 52
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
QUEUE_SIZE = 96
THREAD_EXIT = 97
APPLIST_UPDATE_START = 53
APPLIST_UPDATE_SUCCESS = 54
APPLIST_UPDATE_FAIL = 55


def _mb_text(id):
    return (STRINGS['MOUSE_BUTTON_LEFT'], STRINGS['MOUSE_BUTTON_MIDDLE'], STRINGS['MOUSE_BUTTON_RIGHT'])[id]


class Notify(object):
    
    def __init__(self):
        self.reset()
        
    def __call__(self, message_id, *args):
        
        q0 = self.message_queue[0].append
        q1 = self.message_queue[1].append
        q2 = self.message_queue[2].append
        if message_id == MESSAGE_DEBUG:
            q2('Debug: {}'.format(args))
        if message_id == MOUSE_UNDETECTED:
            q2(STRINGS['MOUSE_NOT_DETECTED'])
        if message_id == MOUSE_DETECTED:
            q2(STRINGS['MOUSE_DETECTED'])
        if message_id == MOUSE_OFFSCREEN:
            q1(STRINGS['MOUSE_OFFSCREEN'])
        if message_id == MOUSE_ONSCREEN:
            q1(STRINGS['MOUSE_ONSCREEN'])
        if message_id == MOUSE_POSITION:
            q0(STRINGS['MOUSE_POSITION'].format(X=args[0][0], Y=args[0][1]))
        if message_id == MOUSE_CLICKED:
            q1(STRINGS['MOUSE_CLICKED'].format(MB=_mb_text(args[1]),
                                          X=args[0][0], Y=args[0][1]))
        if message_id == MOUSE_CLICKED_OFFSCREEN:
            q1(STRINGS['MOUSE_CLICKED_OFFSCREEN'].format(MB=_mb_text(args[1])))
        if message_id == MOUSE_CLICKED_HELD:
            q1(STRINGS['MOUSE_CLICKED_HELD'].format(MB=_mb_text(args[1]),
                                               X=args[0][0], Y=args[0][1]))
        if message_id == MOUSE_UNCLICKED:
            q0(STRINGS['MOUSE_UNCLICKED'])
        if message_id == MOUSE_HELD:
            q1(STRINGS['MOUSE_HELD'])
        if message_id == TRACK_COMPRESS_START:
            q2(STRINGS['TRACK_COMPRESS_START'])
        if message_id == TRACK_COMPRESS_END:
            q2(STRINGS['TRACK_COMPRESS_END'])
        if message_id == RESOLUTION_CHANGED:
            q2(STRINGS['RESOLUTION_CHANGED'].format(X1=args[0][0], Y1=args[0][1],
                                               X2=args[1][0], Y2=args[1][1]))
        if message_id == MONITOR_CHANGED:
            q1(STRINGS['MONITOR_CHANGED'].format(X1=args[0][0], Y1=args[0][1],
                                            X2=args[1][0], Y2=args[1][1]))
        if message_id == KEYBOARD_PRESSES:
            single = STRINGS['PRESS_SINGLE']
            plural = STRINGS['PRESS_PLURAL']
            q1(STRINGS['KEYBOARD_PRESSES'].format(K=', '.join(*args),
                                             P=single if len(args[0]) == 1 else plural))
        if message_id == KEYBOARD_PRESSES_HELD:
            single = STRINGS['PRESS_SINGLE']
            plural = STRINGS['PRESS_PLURAL']
            q1(STRINGS['KEYBOARD_PRESSES_HELD'].format(K=', '.join(*args),
                                                  P=single if len(args[0]) == 1 else plural))
        if message_id == APPLICATION_STARTED:
            q2(STRINGS['APPLICATION_STARTED'].format(A=args[0][0]))
        if message_id == APPLICATION_LOADING:
            default = False
            try:
                if args[0][0] is None:
                    raise TypeError()
            except (IndexError, TypeError):
                profile = DEFAULT_NAME
            else:
                profile = args[0][0]
            q2(STRINGS['APPLICATION_LOADING'].format(A=profile))
        if message_id == APPLICATION_QUIT:
            q2(STRINGS['APPLICATION_QUIT'])
        if message_id == APPLICATION_RELOAD:
            q1(STRINGS['APPLICATION_RELOAD'])
        if message_id == APPLICATION_LISTEN:
            q1(STRINGS['APPLICATION_LISTEN'])
        if message_id == APPLIST_UPDATE_START:
            q1(STRINGS['APPLIST_UPDATE_START'])
        if message_id == APPLIST_UPDATE_SUCCESS:
            q1(STRINGS['APPLIST_UPDATE_SUCCESS'])
        if message_id == APPLIST_UPDATE_FAIL:
            q1(STRINGS['APPLIST_UPDATE_FAIL'])
        if message_id == SAVE_START:
            q2(STRINGS['SAVE_START'])
        if message_id == SAVE_SUCCESS:
            q2(STRINGS['SAVE_SUCCESS'])
        if message_id == SAVE_FAIL:
            q2(STRINGS['SAVE_FAIL'])
        if message_id == SAVE_FAIL_RETRY:
            single = STRINGS['SECOND_SINGLE']
            plural = STRINGS['SECOND_PLURAL']
            q2(STRINGS['SAVE_FAIL_RETRY'].format(T=args[0], S=single if args[0] == 1 else plural,
                              C=args[1] + 1, M=args[2]))
        if message_id == SAVE_FAIL_END:
                q2(STRINGS['SAVE_FAIL_END'])
        if message_id == SAVE_SKIP:
            if args[1] > 2:
                q2(STRINGS['SAVE_SKIP_NO_CHANGE'])
            else:
                single = STRINGS['SECOND_SINGLE']
                plural = STRINGS['SECOND_PLURAL']
                q2(STRINGS['SAVE_SKIP_INACTIVE'].format(T=args[0], S=single if args[0] == 1 else plural))
        if message_id == SAVE_PREPARE:
            q2(STRINGS['SAVE_PREPARE'])
        if message_id == START_MAIN:
            q2(STRINGS['START_MAIN'])
        if message_id == START_THREAD:
            q2(STRINGS['START_THREAD'])
        if message_id == DATA_LOADED:
            q1(STRINGS['DATA_LOADED'])
        if message_id == DATA_NOTFOUND:
            q1(STRINGS['DATA_NOTFOUND'])
        if message_id == QUEUE_SIZE:
            single = STRINGS['COMMAND_SINGLE']
            plural = STRINGS['COMMAND_PLURAL']
            q1(STRINGS['COMMAND_COUNT'].format(N=args[0], C=single if args[0] == 1 else plural))

    def get_output(self):
        allowed_levels = range(CONFIG['Advanced']['MessageLevel'], 3)
        output = [u' | '.join(self.message_queue[i]) for i in allowed_levels][::-1]
        self.reset()
        message = u' | '.join(i for i in output if i)
        return message

    def send(self, q):
        output = self.get_output()
        if output:
            q.put(output)

    def reset(self):
        self.message_queue = {0: [], 1: [], 2: []}

    
NOTIFY = Notify()
