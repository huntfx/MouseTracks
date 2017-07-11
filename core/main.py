from __future__ import division
from multiprocessing import Process, Queue
from threading import Thread
import time

from core.basic import get_items
from core.config import CONFIG
from core.misc import RefreshRateLimiter, error_output
from core.messages import time_format, print_override
from core.notify import *
from core.os import monitor_info, get_cursor_pos, get_mouse_click, get_key_press, KEYS, MULTI_MONITOR
from core.track import background_process, running_processes, monitor_offset


class ThreadHelper(Thread):
    """Run a function in a background thread."""
    def __init__(self, function, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        Thread.__init__(self)
        self.function = function

    def run(self):
        self.function(*self.args, **self.kwargs)


def start_tracking():
    
    mouse_inactive_delay = 2

    updates_per_second = CONFIG['Main']['UpdatesPerSecond']
    timer = {'UpdateScreen': CONFIG['Timer']['CheckResolution'],
             'UpdatePrograms': CONFIG['Timer']['CheckPrograms'],
             'Save': CONFIG['Save']['Frequency'],
             'ReloadProgramList': CONFIG['Timer']['ReloadPrograms'],
             'UpdateQueuedCommands': CONFIG['Timer']['_ShowQueuedCommands']}
    timer = {k: v * updates_per_second for k, v in get_items(timer)}

    store = {'Resolution': {'Current': monitor_info(),
                            'Previous': None,
                            'Boundaries': None},
             'Mouse': {'Position': {'Current': None,
                                    'Previous': None},
                       'NotMoved': 0,
                       'Inactive': False,
                       'Clicked': {},
                       'OffScreen': False},
             'Keyboard': {'KeysPressed': {k: False for k in KEYS.keys()}},
             'LastActivity': 0,
             'LastSent': 0,
             'Save': {'Finished': True,
                      'Next': timer['Save']}
            }
    mouse_pos = store['Mouse']['Position']
    
    #Start background process
    q_send = Queue()
    q_recv = Queue()
    p = Process(target=background_process, args=(q_send, q_recv))
    #p.daemon = True
    p.start()

    q_send2 = Queue()
    q_recv2 = Queue()
    running_programs = ThreadHelper(running_processes, q_send2, q_recv2, q_send)
    running_programs.start()
    
    i = 0
    NOTIFY(START_MAIN)
    while True:
        with RefreshRateLimiter(updates_per_second) as limiter:
            
            #Send data to thread
            try:
                if frame_data or frame_data_rp:
                    last_sent = i - store['LastSent']
                    if frame_data:
                        if last_sent:
                            frame_data['Ticks'] = last_sent
                        q_send.put(frame_data)
                    if frame_data_rp:
                        q_send2.put(frame_data_rp)
                    store['LastSent'] = i
            except NameError:
                pass
            
            while not q_recv2.empty():
                print_override('{} {}'.format(time_format(limiter.time), q_recv2.get()))
            
            #Print any messages from previous loop
            notify_extra = ''
            received_data = []
            while not q_recv.empty():
            
                received_message = q_recv.get()
                
                #Receive text messages
                try:
                    if received_message.startswith('Traceback (most recent call last)'):
                        return received_message
                except AttributeError:
                    pass
                else:
                    received_data.append(received_message)
                
                #Get notification when saving is finished
                try:
                    received_message.pop('SaveFinished')
                except (KeyError, AttributeError):
                    pass
                else:
                    store['Save']['Finished'] = True
                    store['Save']['Next'] = i + timer['Save']
                
            if received_data:
                notify_extra = u' | '.join(received_data)
            notify_output = NOTIFY.get_output()
            
            if notify_extra:
                if notify_output:
                    notify_output = notify_extra + ' | ' + notify_output
                else:
                    notify_output = notify_extra
            if notify_output:
                print_override(u'{} {}'.format(time_format(limiter.time), notify_output))

            frame_data = {}
            frame_data_rp = {}
            mouse_pos['Current'] = get_cursor_pos()

            #Check if mouse is inactive (such as in a screensaver)
            if mouse_pos['Current'] is None:
                if not store['Mouse']['Inactive']:
                    NOTIFY(MOUSE_UNDETECTED)
                    store['Mouse']['Inactive'] = True
                time.sleep(mouse_inactive_delay)
                continue

            #Check if mouse left the monitor
            elif (not MULTI_MONITOR
                  and (not 0 <= mouse_pos['Current'][0] < store['Resolution']['Current'][0]
                       or not 0 <= mouse_pos['Current'][1] < store['Resolution']['Current'][1])):
                if not store['Mouse']['OffScreen']:
                    NOTIFY(MOUSE_OFFSCREEN)
                    store['Mouse']['OffScreen'] = True
            elif store['Mouse']['OffScreen']:
                NOTIFY(MOUSE_ONSCREEN)
                store['Mouse']['OffScreen'] = False

            #Notify once if mouse is no longer inactive
            if store['Mouse']['Inactive']:
                store['Mouse']['Inactive'] = False
                NOTIFY(MOUSE_DETECTED)

            #Check if mouse is in a duplicate position
            if mouse_pos['Current'] is None or mouse_pos['Current'] == mouse_pos['Previous']:
                store['Mouse']['NotMoved'] += 1
            elif store['Mouse']['NotMoved']:
                store['Mouse']['NotMoved'] = 0
            if not store['Mouse']['NotMoved']:
                if not store['Mouse']['OffScreen']:
                    frame_data['MouseMove'] = (mouse_pos['Previous'], mouse_pos['Current'])
                    NOTIFY(MOUSE_POSITION, mouse_pos['Current'])
                    store['LastActivity'] = i

            #Mouse clicks
            click_repeat = CONFIG['Main']['RepeatClicks']
            for mouse_button, clicked in enumerate(get_mouse_click()):

                mb_clicked = store['Mouse']['Clicked'].get(mouse_button, False)
                mb_data = (mouse_button, mouse_pos['Current'])
                
                if clicked:
                    store['LastActivity'] = i
                    
                    #First click
                    if not mb_clicked:
                        store['Mouse']['Clicked'][mouse_button] = limiter.time
                        if not store['Mouse']['OffScreen']:
                            NOTIFY(MOUSE_CLICKED, mouse_pos['Current'], mouse_button)
                            try:
                                frame_data['MouseClick'].append(mb_data)
                            except KeyError:
                                frame_data['MouseClick'] = [mb_data]
                        else:
                            NOTIFY(MOUSE_CLICKED_OFFSCREEN, mouse_button)
                            
                    #Held clicks
                    elif click_repeat and mb_clicked < limiter.time - click_repeat:
                        store['Mouse']['Clicked'][mouse_button] = limiter.time
                        if not store['Mouse']['OffScreen']:
                            NOTIFY(MOUSE_CLICKED_HELD, mouse_pos['Current'], mouse_button)
                            try:
                                frame_data['MouseClick'].append(mb_data)
                            except KeyError:
                                frame_data['MouseClick'] = [mb_data]
                elif mb_clicked:
                    NOTIFY(MOUSE_UNCLICKED)
                    del store['Mouse']['Clicked'][mouse_button]
                    store['LastActivity'] = i
 
            
            #Key presses
            keys_pressed = []
            keys_held = []
            key_status = store['Keyboard']['KeysPressed']
            key_press_repeat = CONFIG['Main']['RepeatKeyPress']
            _keys_held = []
            _keys_pressed = []
            for k in KEYS:
                if get_key_press(KEYS[k]):
                    keys_held.append(k)
                    
                    #If key is currently being held down
                    if key_status[k]:
                        if key_press_repeat and key_status[k] < limiter.time - key_press_repeat:
                            keys_pressed.append(k)
                            _keys_held.append(k)
                            key_status[k] = limiter.time

                    #If key has been pressed
                    else:
                        keys_pressed.append(k)
                        _keys_pressed.append(k)
                        key_status[k] = limiter.time
                        notify_key_press = list(keys_pressed)

                #If key has been released
                elif key_status[k]:
                    key_status[k] = False
                    
            if keys_pressed:
                frame_data['KeyPress'] = keys_pressed
            if keys_held:
                frame_data['KeyHeld'] = keys_held
                store['LastActivity'] = i
            if _keys_held:
                NOTIFY(KEYBOARD_PRESSES_HELD, _keys_held)
            if _keys_pressed:
                NOTIFY(KEYBOARD_PRESSES, _keys_pressed)

            #Check if resolution has changed
            if not i % timer['UpdateScreen']:
            
                if MULTI_MONITOR:
                    frame_data['MonitorLimits'] = monitor_info()
                    store['Resolution']['Boundaries'] = frame_data['MonitorLimits']
                else:
                    store['Resolution']['Current'] = monitor_info()
                    if store['Resolution']['Previous'] != store['Resolution']['Current']:
                        if store['Resolution']['Previous'] is not None:
                            NOTIFY(RESOLUTION_CHANGED, store['Resolution']['Previous'], store['Resolution']['Current'])
                        frame_data['Resolution'] = ['Resolution']['Current']
                        store['Resolution']['Previous'] = store['Resolution']['Current']
            
            #Display message that mouse has switched monitors
            if MULTI_MONITOR and 'MouseMove' in frame_data:
                
                try:
                    try:
                        res = monitor_offset(frame_data['MouseMove'][1], store['Resolution']['Boundaries'])[0]
                    except TypeError:
                        frame_data['MonitorLimits'] = monitor_info()
                        store['Resolution']['Boundaries'] = frame_data['MonitorLimits']
                        res = monitor_offset(frame_data['MouseMove'][1], store['Resolution']['Boundaries'])[0]
                except TypeError:
                    pass
                else:
                    store['Resolution']['Current'] = res
                    if store['Resolution']['Previous'] is not None:
                        if store['Resolution']['Current'] != store['Resolution']['Previous']:
                            NOTIFY(MONITOR_CHANGED, store['Resolution']['Previous'], store['Resolution']['Current'])
                    store['Resolution']['Previous'] = store['Resolution']['Current']

            #Send request to update programs
            if not i % timer['UpdatePrograms']:
                frame_data_rp['Update'] = True
            
            
            #Send request to reload program list
            if not i % timer['ReloadProgramList']:
                frame_data_rp['Reload'] = True

            #Update user about the queue size
            if not i % timer['UpdateQueuedCommands'] and store['LastActivity'] > i - timer['Save']:
                NOTIFY(QUEUE_SIZE, q_send.qsize())
            
            #Send save request
            if store['Save']['Finished'] and i and not i % store['Save']['Next']:
                frame_data['Save'] = True
                store['Save']['Finished'] = False

            if store['Mouse']['OffScreen']:
                mouse_pos['Previous'] = None
            else:
                mouse_pos['Previous'] = mouse_pos['Current']
            i += 1
            
