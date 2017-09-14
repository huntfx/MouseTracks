from __future__ import division, absolute_import
from multiprocessing import Process, Queue
from threading import Thread
import time
import traceback

from core.compatibility import get_items, _print
from core.config import CONFIG
from core.constants import UPDATES_PER_SECOND
from core.error import handle_error
from core.messages import time_format
from core.notify import *
from core.os import monitor_info, get_cursor_pos, get_mouse_click, get_key_press, KEYS, MULTI_MONITOR, get_double_click_time
from core.track.background import background_process, running_processes, monitor_offset


class RefreshRateLimiter(object):
    """Limit the loop to a fixed updates per second.
    It works by detecting how long a frame should be,
    and comparing it to how long it's already taken.
    """
    def __init__(self, ticks):
        self.time = time.time()
        self.frame_time = 1 / ticks

    def __enter__(self):
        return self

    def __exit__(self, *args):
        time_difference = time.time() - self.time
        time.sleep(max(0, self.frame_time - time_difference))


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
    
    _background_process = None
    no_detection_wait = 2
    
    try:
        NOTIFY(MT_PATH)
        _print(u'{} {}'.format(time_format(time.time()), NOTIFY.get_output()))
        CONFIG.save()
        

        timer = {'UpdateScreen': CONFIG['Advanced']['CheckResolution'],
                 'UpdatePrograms': CONFIG['Advanced']['CheckRunningApplications'],
                 'Save': CONFIG['Save']['Frequency'] * UPDATES_PER_SECOND,
                 'ReloadProgramList': CONFIG['Advanced']['ReloadApplicationList'],
                 'UpdateQueuedCommands': CONFIG['Advanced']['ShowQueuedCommands']}
                 
        store = {'Resolution': {'Current': monitor_info(),
                                'Previous': None,
                                'Boundaries': None},
                 'Mouse': {'Position': {'Current': None,
                                        'Previous': None},
                           'NotMoved': 0,
                           'Inactive': False,
                           'Clicked': {},
                           'LastClickTime': 0,
                           'OffScreen': False,
                           'DoubleClickTime': get_double_click_time() / 1000},
                 'Keyboard': {'KeysPressed': {k: False for k in KEYS.keys()}},
                 'LastActivity': 0,
                 'LastSent': 0,
                 'Save': {'Finished': True,
                          'Next': timer['Save']}
                }
        mouse_pos = store['Mouse']['Position']
        
        #Start background processes
        q_bg_send = Queue()
        q_bg_recv = Queue()
        _background_process = Process(target=background_process, args=(q_bg_send, q_bg_recv))
        _background_process.daemon = True
        _background_process.start()
        
        q_rp_send = Queue()
        q_rp_recv = Queue()
        _running_programs = ThreadHelper(running_processes, q_rp_send, q_rp_recv, q_bg_send)
        _running_programs.daemon = True
        _running_programs.start()
        
        i = 0
        NOTIFY(START_MAIN)
        _print(u'{} {}'.format(time_format(time.time()), NOTIFY.get_output()))
        while True:
            with RefreshRateLimiter(UPDATES_PER_SECOND) as limiter:
                
                #Send data to thread
                try:
                    if frame_data or frame_data_rp:
                        last_sent = i - store['LastSent']
                        if frame_data:
                            if last_sent:
                                frame_data['Ticks'] = last_sent
                            q_bg_send.put(frame_data)
                        if frame_data_rp:
                            q_rp_send.put(frame_data_rp)
                        store['LastSent'] = i
                except NameError:
                    pass
                
                while not q_rp_recv.empty():
                    _print(u'{} {}'.format(time_format(limiter.time), q_rp_recv.get()))
                
                #Print any messages from previous loop
                notify_extra = ''
                received_data = []
                while not q_bg_recv.empty():
                
                    received_message = q_bg_recv.get()
                    
                    #Receive text messages
                    try:
                        if received_message.startswith('Traceback (most recent call last)'):
                            q_bg_send.put({'Quit': True})
                            handle_error(received_message)
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
                    _print(u'{} {}'.format(time_format(limiter.time), notify_output))

                frame_data = {}
                frame_data_rp = {}
                mouse_pos['Current'] = get_cursor_pos()

                #Check if mouse is inactive (such as in a screensaver)
                if mouse_pos['Current'] is None:
                    if not store['Mouse']['Inactive']:
                        NOTIFY(MOUSE_UNDETECTED)
                        store['Mouse']['Inactive'] = True
                    time.sleep(no_detection_wait)
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
                click_repeat = CONFIG['Advanced']['RepeatClicks']
                for mouse_button, clicked in enumerate(get_mouse_click()):

                    mb_clicked = store['Mouse']['Clicked'].get(mouse_button, False)
                    mb_data = (mouse_button, mouse_pos['Current'])
                    
                    if clicked:
                        store['LastActivity'] = i
                        
                        #First click
                        if not mb_clicked:           
                            
                            #Double click     
                            double_click = False
                            if store['Mouse']['LastClickTime'] > limiter.time - store['Mouse']['DoubleClickTime']:
                                store['Mouse']['LastClickTime'] = 0
                                double_click = True
                            else:
                                store['Mouse']['LastClickTime'] = limiter.time
                            
                            #Single click
                            store['Mouse']['Clicked'][mouse_button] = limiter.time
                            
                            if not store['Mouse']['OffScreen']:
                                if double_click:
                                    NOTIFY(MOUSE_CLICKED_DOUBLE, mouse_button, mouse_pos['Current'])
                                else:
                                    NOTIFY(MOUSE_CLICKED, mouse_button, mouse_pos['Current'])
                                try:
                                    frame_data['MouseClick'].append(mb_data)
                                except KeyError:
                                    frame_data['MouseClick'] = [mb_data]
                                frame_data['MouseHeld'] = False
                            else:
                                if double_click:
                                    NOTIFY(MOUSE_CLICKED_DOUBLE, mouse_button)
                                else:
                                    NOTIFY(MOUSE_CLICKED, mouse_button)
                                
                        #Held clicks
                        elif click_repeat and mb_clicked < limiter.time - click_repeat:
                            store['Mouse']['Clicked'][mouse_button] = limiter.time
                            if not store['Mouse']['OffScreen']:
                                NOTIFY(MOUSE_CLICKED_HELD, mouse_button, mouse_pos['Current'])
                                try:
                                    frame_data['MouseClick'].append(mb_data)
                                except KeyError:
                                    frame_data['MouseClick'] = [mb_data]
                                frame_data['MouseHeld'] = True
                            else:
                                NOTIFY(MOUSE_CLICKED_HELD, mouse_button)
                                
                    elif mb_clicked:
                        NOTIFY(MOUSE_UNCLICKED)
                        del store['Mouse']['Clicked'][mouse_button]
                        store['LastActivity'] = i
     
                
                #Key presses
                keys_pressed = []
                keys_held = []
                key_status = store['Keyboard']['KeysPressed']
                key_press_repeat = CONFIG['Advanced']['RepeatKeyPress']
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

                recalculate_mouse = False
                
                #Check if resolution has changed
                if timer['UpdateScreen'] and not i % timer['UpdateScreen']:
                
                    if MULTI_MONITOR:
                        try:
                            old_resolution = list(store['Resolution']['Boundaries'])
                        except TypeError:
                            old_resolution = None
                        store['Resolution']['Boundaries'] = monitor_info()
                        frame_data['MonitorLimits'] = store['Resolution']['Boundaries']
                        if old_resolution != store['Resolution']['Boundaries']:
                            recalculate_mouse = True
                    else:
                        store['Resolution']['Current'] = monitor_info()
                        if store['Resolution']['Previous'] != store['Resolution']['Current']:
                            if store['Resolution']['Previous'] is not None:
                                NOTIFY(RESOLUTION_CHANGED, store['Resolution']['Previous'], store['Resolution']['Current'])
                            frame_data['Resolution'] = ['Resolution']['Current']
                            store['Resolution']['Previous'] = store['Resolution']['Current']
                
                #Display message that mouse has switched monitors
                if MULTI_MONITOR:
                    try:
                        current_mouse_pos = frame_data['MouseMove'][1]
                    except KeyError:
                        current_mouse_pos = mouse_pos['Current']
                    else:
                        recalculate_mouse = True
                    
                    if recalculate_mouse:
                        try:
                            try:
                                res = monitor_offset(current_mouse_pos, store['Resolution']['Boundaries'])[0]
                            except TypeError:
                                frame_data['MonitorLimits'] = monitor_info()
                                store['Resolution']['Boundaries'] = frame_data['MonitorLimits']
                                res = monitor_offset(current_mouse_pos, store['Resolution']['Boundaries'])[0]
                        except TypeError:
                            pass
                        else:
                            store['Resolution']['Current'] = res
                            if store['Resolution']['Previous'] is not None:
                                if store['Resolution']['Current'] != store['Resolution']['Previous']:
                                    NOTIFY(MONITOR_CHANGED, store['Resolution']['Previous'], store['Resolution']['Current'])
                            store['Resolution']['Previous'] = store['Resolution']['Current']

                #Send request to update programs
                if timer['UpdatePrograms'] and not i % timer['UpdatePrograms']:
                    frame_data_rp['Update'] = True
                
                
                #Send request to reload program list
                if timer['ReloadProgramList'] and not i % timer['ReloadProgramList']:
                    frame_data_rp['Reload'] = True

                #Update user about the queue size
                if (timer['UpdateQueuedCommands'] and not i % timer['UpdateQueuedCommands'] 
                        and timer['Save'] and store['LastActivity'] > i - timer['Save']):
                    try:
                        NOTIFY(QUEUE_SIZE, q_bg_send.qsize())
                    except NotImplementedError:
                        pass
                
                #Send save request
                if store['Save']['Finished'] and i and not i % store['Save']['Next']:
                    frame_data['Save'] = True
                    store['Save']['Finished'] = False

                if store['Mouse']['OffScreen']:
                    mouse_pos['Previous'] = None
                else:
                    mouse_pos['Previous'] = mouse_pos['Current']
                i += 1
            
    except Exception as e:
        if _background_process is not None:
            try:
                q_bg_send.put({'Quit': True})
            except IOError:
                pass
        handle_error(traceback.format_exc())
        
    except KeyboardInterrupt:
        if _background_process is not None:
            try:
                q_bg_send.put({'Quit': True})
            except IOError:
                pass
        NOTIFY(THREAD_EXIT)
        NOTIFY(PROCESS_EXIT)
        _print(u'{} {}'.format(time_format(time.time()), NOTIFY.get_output()))
        handle_error()
