from datetime import datetime
from constants import DEFAULT_NAME

MESSAGE_LEVEL = 1

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
MOUSE_COMPRESS_START = 13
MOUSE_COMPRESS_END = 14
RESOLUTION_CHANGED = 16
KEYBOARD_PRESSES = 32
KEYBOARD_PRESSES_HELD = 33
PROGRAM_STARTED = 48
PROGRAM_QUIT = 49
PROGRAM_RELOAD = 50
PROGRAM_LISTEN = 51
PROGRAM_LOADING = 52
SAVE_START = 64
SAVE_SUCCESS = 65
SAVE_FAIL = 66
SAVE_FAIL_RETRY = 67
SAVE_FAIL_END = 68
SAVE_SKIP = 69
START_MAIN = 80
START_THREAD = 81
DATA_LOADED = 82
DATA_NOTFOUND = 83
QUEUE_SIZE = 96


def _mb_text(id):
    return ('Left', 'Middle', 'Right')[id]


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
            q2('Unable to read cursor position (usually happens when user is away).')
        if message_id == MOUSE_DETECTED:
            q2('Cursor position has been detected again.')
        if message_id == MOUSE_OFFSCREEN:
            q1('Cursor has left the main monitor.')
        if message_id == MOUSE_ONSCREEN:
            q1('Cursor has entered the main monitor.')
        if message_id == MOUSE_POSITION:
            q0('Cursor position: ({}, {})'.format(args[0][0], args[0][1]))
        if message_id == MOUSE_CLICKED:
            q1('{} mouse button clicked at ({}, {})'.format(_mb_text(args[1]),
                                                            args[0][0], args[0][1]))
        if message_id == MOUSE_CLICKED_OFFSCREEN:
            q1('{} mouse button clicked.'.format(_mb_text(args[0])))
        if message_id == MOUSE_CLICKED_HELD:
            q1('{} mouse button being held at ({}, {})'.format(_mb_text(args[1]),
                                                               args[0][0], args[0][1]))
        if message_id == MOUSE_UNCLICKED:
            q0('Mouse button unclicked.')
        if message_id == MOUSE_HELD:
            q1('Mouse button being held.')
        if message_id == MOUSE_COMPRESS_START:
            if args[0] == 'track':
                q2('Tracking data is being compressed...')
            elif args[0] == 'speed':
                q2('Speed data is being compressed...')
        if message_id == MOUSE_COMPRESS_END:
            if args[0] == 'track':
                q2('Finished compressing tracking data.')
            elif args[0] == 'speed':
                q2('Finished compressing speed data.')
        if message_id == RESOLUTION_CHANGED:
            q2('Resolution changed from {}x{} to {}x{}'.format(args[0][0], args[0][1],
                                                               args[1][0], args[1][1]))
        if message_id == KEYBOARD_PRESSES:
            q1('Key Presses: {}'.format(', '.join(*args)))
        if message_id == KEYBOARD_PRESSES_HELD:
            q1('Key Presses (held down): {}'.format(', '.join(*args)))
        if message_id == PROGRAM_STARTED:
            q2('Program detected: {}'.format(args[0][0]))
        if message_id == PROGRAM_LOADING:
            default = False
            try:
                if args[0][0] is None:
                    raise TypeError()
            except (IndexError, TypeError):
                profile = DEFAULT_NAME
            else:
                profile = args[0][0]
            q2('Switching profile to {}.'.format(profile))
        if message_id == PROGRAM_QUIT:
            q2('Program quit.')
        if message_id == PROGRAM_RELOAD:
            q1('Finished reloading program list.')
        if message_id == PROGRAM_LISTEN:
            q1('Started checking for running programs.')
        if message_id == SAVE_START:
            q2('Saving the file...')
        if message_id == SAVE_SUCCESS:
            q2('Finished saving.')
        if message_id == SAVE_FAIL:
            q2('Unable to save file, make sure this has the correct permissions.')
        if message_id == SAVE_FAIL_RETRY:
            q2('Unable to save file, trying again in {} second{}.'
               ' (attempt {} of {})'.format(args[0], '' if args[0] == 1 else 's',
                                            args[1] + 1, args[2]))
        if message_id == SAVE_FAIL_END:
            q2('Failed to save file (maximum attempts reached)'
               ', make sure the correct permissions have been granted.')
        if message_id == SAVE_SKIP:
            q2('Skipping save, user inactive for {} second{}.'.format(args[0],
                                                                      '' if args[0] == 1 else 's'))
        if message_id == START_MAIN:
            q2('Started main loop.')
        if message_id == START_THREAD:
            q2('Started background thread.')
        if message_id == DATA_LOADED:
            q1('Finished loading data.')
        if message_id == DATA_NOTFOUND:
            q1('Started new data store.')
        if message_id == QUEUE_SIZE:
            q1('{} command{} queued for processing.'.format(args[0], '' if args[0] == 1 else 's'))

    def __str__(self):
        allowed_levels = range(MESSAGE_LEVEL, 3)
        output = [' | '.join(self.message_queue[i]) for i in allowed_levels][::-1]
        self.reset()
        message = ' | '.join(i for i in output if i)
        return message

    def send(self, q):
        output = str(self)
        if output:
            q.put(output)

    def reset(self):
        self.message_queue = {0: [], 1: [], 2: []}


def time_format(t):
    return '[{}]'.format(datetime.fromtimestamp(t).strftime("%H:%M:%S"))


def date_format(t):
    dt = datetime.fromtimestamp(t)
    hour = dt.hour
    minute = dt.minute
    if 0 <= hour < 12:
        suffix = 'AM'
    else:
        suffix = 'PM'
        hour %= 12
    if not hour:
        hour += 12
    output_time = '{h}:{m}{s}'.format(h=hour, m=minute, s=suffix)
    
    day = str(dt.day)
    if day.endswith('1'):
        day += 'st'
    elif day.endswith('2'):
        day += 'nd'
    elif day.endswith('3'):
        day += 'rd'
    else:
        day += 'th'
    month = dt.strftime("%B")
    year = dt.year
    output_date = '{d} {m} {y}'.format(d=day, m=month, y=year)

    return '{}, {}'.format(output_time, output_date)

    
NOTIFY = Notify()
