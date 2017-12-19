"""
This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""
#The main loop used for tracking, runs 60 times per second

from __future__ import division, absolute_import

import time
import traceback
from multiprocessing import Process, Queue
from threading import Thread

from core.api import *
from core.compatibility import get_items, MessageWithQueue
from core.config import CONFIG
from core.constants import UPDATES_PER_SECOND
from core.error import handle_error
from core.files import Lock
from core.messages import time_format
from core.notify import *
from core.os import monitor_info, get_cursor_pos, get_mouse_click, get_key_press, KEYS, MULTI_MONITOR, get_double_click_time
from core.sockets import get_free_port
from core.track.background import background_process, running_processes, monitor_offset
from core.track.xinput import Gamepad


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
        try:
            time.sleep(max(0, self.frame_time - time_difference))
        except IOError: #Interrupted function call (when quitting program)
            pass

        
def start_tracking():
    """Put a lock on the main script to stop more than one instance running."""
    
    with Lock() as lock:
        if lock:
            _start_tracking()
        else:
            handle_error(NOTIFY(PROCESS_NOT_UNIQUE).get_output(), log=False)
    
    
def _start_tracking():
    
    _background_process = None
    no_detection_wait = 2
    
    try:
        
        #Setup message server
        if CONFIG['API']['RunServer']:
            q_msg = Queue()
            q_feedback = Queue()
            message = MessageWithQueue(q_msg).send
            start_message_server(q_msg, q_feedback=q_feedback)
        else:
            message = MessageWithQueue().send
        
        #Start main script
        NOTIFY(MT_PATH)
        message(u'{} {}'.format(time_format(time.time()), NOTIFY.get_output()))
        CONFIG.save()
        
        #Adjust timings to account for tick rate
        timer = {'UpdateScreen': CONFIG['Advanced']['CheckResolution'],
                 'UpdatePrograms': CONFIG['Advanced']['CheckRunningApplications'],
                 'Save': CONFIG['Save']['Frequency'] * UPDATES_PER_SECOND,
                 'ReloadProgramList': CONFIG['Advanced']['ReloadApplicationList'],
                 'UpdateQueuedCommands': CONFIG['Advanced']['ShowQueuedCommands'],
                 'RefreshGamepads': CONFIG['Advanced']['RefreshGamepads'],
                 'HistoryCheck': CONFIG['Advanced']['HistoryCheck']}
                 
        store = {'Resolution': {'Current': monitor_info(),
                                'Previous': None,
                                'Boundaries': None},
                 'Mouse': {'Position': {'Current': None,
                                        'Previous': None},
                           'NotMoved': 0,
                           'Inactive': False,
                           'Clicked': {},
                           'LastClick': None,
                           'LastClickTime': 0,
                           'OffScreen': False,
                           'DoubleClickTime': get_double_click_time() / 1000 * UPDATES_PER_SECOND},
                 'Keyboard': {'KeysPressed': {k: False for k in KEYS.keys()}},
                 'LastActivity': 0,
                 'LastSent': 0,
                 'Save': {'Finished': True,
                          'Next': timer['Save']},
                 'Gamepad': {'ButtonsPressed': {}},
                 'FlaskApp': None
                }
        mouse_pos = store['Mouse']['Position']
            
        #Setup web server
        if CONFIG['API']['RunWeb']:
            store['FlaskApp'] = app
            store['FlaskApp'].config.update(create_pipe('REQUEST', duplex=False))
            store['FlaskApp'].config.update(create_pipe('CONTROL', duplex=False))
            store['FlaskApp'].config.update(create_pipe('STATUS', duplex=False))
            
            web_port = get_free_port()
            start_web_server(app, web_port)
        
        #Start background processes
        q_bg_recv = Queue()
        q_bg_send = Queue()
        _background_process = Process(target=background_process, args=(q_bg_send, q_bg_recv))
        _background_process.daemon = True
        _background_process.start()
        
        q_rp_recv = Queue()
        q_rp_send = Queue()
        _running_programs = Thread(target=running_processes, args=(q_rp_send, q_rp_recv, q_bg_send))
        _running_programs.daemon = True
        _running_programs.start()
        
        ticks = 0
        NOTIFY(START_MAIN)
        message(u'{} {}'.format(time_format(time.time()), NOTIFY.get_output()))
        script_status = STATUS_RUNNING
        while script_status != STATUS_TERMINATED:
            with RefreshRateLimiter(UPDATES_PER_SECOND) as limiter:
                
                #Handle web server API requests
                if store['FlaskApp'] is not None:
                    
                    #Control state of script
                    if app.config['PIPE_CONTROL_RECV'].poll():
                        script_status = app.config['PIPE_CONTROL_RECV'].recv()
                    
                    #Requests that require response
                    if store['FlaskApp'].config['PIPE_REQUEST_RECV'].poll():
                        request_id = store['FlaskApp'].config['PIPE_REQUEST_RECV'].recv()
                        if request_id == FEEDBACK_STATUS:
                            store['FlaskApp'].config['PIPE_STATUS_SEND'].send(script_status)
                        elif request_id == FEEDBACK_PORT:
                            #TODO: send actual ports
                            store['FlaskApp'].config['PIPE_STATUS_SEND'].send((0, 1))
                    
                if script_status != STATUS_RUNNING:
                    continue
                
                #Send data to thread
                try:
                    if frame_data or frame_data_rp:
                        last_sent = ticks - store['LastSent']
                        if frame_data:
                            if last_sent:
                                frame_data['Ticks'] = last_sent
                            q_bg_send.put(frame_data)
                        if frame_data_rp:
                            q_rp_send.put(frame_data_rp)
                        store['LastSent'] = ticks
                except NameError:
                    pass
                
                while not q_rp_recv.empty():
                    message(u'{} {}'.format(time_format(limiter.time), q_rp_recv.get()))
                
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
                        store['Save']['Next'] = ticks + timer['Save']
                
                output_list = [received_data]
                    
                #Add on output from Notify class
                output_list.append(NOTIFY.get_output())
                
                #Add output from server
                if CONFIG['API']['RunServer']:
                    received_data = []
                    while not q_feedback.empty():
                        received_data.append(q_feedback.get())
                    output_list.append(received_data)
                
                #Join all valid outputs together
                output = u' | '.join(u' | '.join(msg_group) if isinstance(msg_group, (list, tuple)) else msg_group
                                     for msg_group in output_list if msg_group)
                if output:
                    message(u'{} {}'.format(time_format(limiter.time), output))

                frame_data = {}
                frame_data_rp = {}
                
                
                #Mouse Movement
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
                        store['LastActivity'] = ticks

                        
                #Mouse clicks
                click_repeat = CONFIG['Advanced']['RepeatClicks']
                for mouse_button, clicked in enumerate(get_mouse_click()):

                    mb_clicked = store['Mouse']['Clicked'].get(mouse_button, False)
                    mb_data = (mouse_button, mouse_pos['Current'])
                    
                    if clicked:
                        store['LastActivity'] = ticks
                        
                        #First click
                        if not mb_clicked:           
                            
                            #Double click     
                            double_click = False
                            if (store['Mouse']['LastClickTime'] > ticks - store['Mouse']['DoubleClickTime']
                                    and store['Mouse']['LastClick'] == mb_data):
                                store['Mouse']['LastClickTime'] = 0
                                store['Mouse']['LastClick'] = None
                                double_click = True
                                try:
                                    frame_data['DoubleClick'].append(mb_data)
                                except KeyError:
                                    frame_data['DoubleClick'] = [mb_data]
                            else:
                                store['Mouse']['LastClickTime'] = ticks
                            
                            #Single click
                            store['Mouse']['Clicked'][mouse_button] = ticks
                            
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
                        elif click_repeat and mb_clicked < ticks - click_repeat:
                            store['Mouse']['Clicked'][mouse_button] = ticks
                            if not store['Mouse']['OffScreen']:
                                NOTIFY(MOUSE_CLICKED_HELD, mouse_button, mouse_pos['Current'])
                                try:
                                    frame_data['MouseClick'].append(mb_data)
                                except KeyError:
                                    frame_data['MouseClick'] = [mb_data]
                                frame_data['MouseHeld'] = True
                            else:
                                NOTIFY(MOUSE_CLICKED_HELD, mouse_button)
                                
                        store['Mouse']['LastClick'] = mb_data
                        
                    elif mb_clicked:
                        NOTIFY(MOUSE_UNCLICKED)
                        del store['Mouse']['Clicked'][mouse_button]
                        store['LastActivity'] = ticks
     
     
                #Key presses
                keys_pressed = []
                keys_held = []
                key_status = store['Keyboard']['KeysPressed']
                key_press_repeat = CONFIG['Advanced']['RepeatKeyPress']
                _keys_held = []
                _keys_pressed = []
                _keys_released = []
                for k in KEYS:
                    if get_key_press(KEYS[k]):
                        keys_held.append(k)
                        
                        #If key is currently being held down
                        if key_status[k]:
                            if key_press_repeat and key_status[k] < ticks - key_press_repeat:
                                keys_pressed.append(k)
                                _keys_held.append(k)
                                key_status[k] = ticks

                        #If key has been pressed
                        else:
                            keys_pressed.append(k)
                            _keys_pressed.append(k)
                            key_status[k] = ticks
                            notify_key_press = list(keys_pressed)

                    #If key has been released
                    elif key_status[k]:
                        key_status[k] = False
                        _keys_released.append(k)
                        
                if keys_pressed:
                    frame_data['KeyPress'] = keys_pressed
                    store['LastActivity'] = ticks
                    
                if keys_held:
                    frame_data['KeyHeld'] = keys_held
                    store['LastActivity'] = ticks
                    
                if _keys_pressed:
                    NOTIFY(KEYBOARD_PRESSES, *_keys_pressed)
                    
                if _keys_held:
                    NOTIFY(KEYBOARD_PRESSES_HELD, *_keys_held)
                    
                if _keys_released:
                    NOTIFY(KEYBOARD_RELEASED, *_keys_released)
                
                
                #Reload list of gamepads (in case one was plugged in)
                if timer['RefreshGamepads'] and not ticks % timer['RefreshGamepads']:
                    try:
                        old_gamepads = set(gamepads)
                    except UnboundLocalError:
                        old_gamepads = set()
                    gamepads = {gamepad.device_number: gamepad for gamepad in Gamepad.list_gamepads()}
                    difference = set(gamepads) - old_gamepads
                    for i, id in enumerate(difference):
                        NOTIFY(GAMEPAD_FOUND, id)
                        store['Gamepad']['ButtonsPressed'][id] = {}
                
                #Gamepad tracking (multiple controllers not tested yet)
                button_repeat = CONFIG['Advanced']['RepeatButtonPress']
                invalid_ids = []
                buttons_held = {}
                _buttons_pressed = {}
                _buttons_released = {}
                
                for id, gamepad in get_items(gamepads):
                    
                    #Repeat presses
                    if button_repeat:
                        for button_id, last_update in get_items(store['Gamepad']['ButtonsPressed'][id]):
                            if last_update < ticks - button_repeat:
                                try:
                                    buttons_held[id].append(button_id)
                                except KeyError:
                                    buttons_held[id] = [button_id]
                                store['Gamepad']['ButtonsPressed'][id][button_id] = ticks
                    
                    with gamepad as gamepad_input:
                    
                        #Break the connection if controller can't be found
                        if not gamepad.connected:
                            NOTIFY(GAMEPAD_LOST, id)
                            invalid_ids.append(id)
                            continue
                        
                        #Axis events (thumbsticks, triggers, etc)
                        #Send an update every tick, but only print the changes
                        #The dead zone can be tracked now and ignored later
                        printable = {}
                        axis_updates = gamepad_input.get_axis(printable=printable)
                        if axis_updates:
                            store['LastActivity'] = ticks
                            try:
                                frame_data['GamepadAxis'].append(axis_updates)
                            except KeyError:
                                frame_data['GamepadAxis'] = [axis_updates]
                            for axis, value in get_items(printable):
                                NOTIFY(GAMEPAD_AXIS, id, axis, value)
                            
                        #Button events
                        button_presses = gamepad_input.get_button()
                        if button_presses:
                            for button_id, state in get_items(button_presses):
                                
                                #Button pressed
                                if state:
                                    try:
                                        frame_data['GamepadButtonPress'].append(button_id)
                                    except KeyError:
                                        frame_data['GamepadButtonPress'] = [button_id]
                                    store['Gamepad']['ButtonsPressed'][id][button_id] = ticks
                                    try:
                                        _buttons_pressed[id].append(button_id)
                                    except KeyError:
                                        _buttons_pressed[id] = [button_id]
                                
                                #Button has been released
                                elif button_id in store['Gamepad']['ButtonsPressed'][id]:
                                    held_length = ticks - store['Gamepad']['ButtonsPressed'][id][button_id]
                                    del store['Gamepad']['ButtonsPressed'][id][button_id]
                                    try:
                                        _buttons_released[id].append(button_id)
                                    except KeyError:
                                        _buttons_released[id] = [button_id]
                
                #Send held buttons each frame
                for id, held_buttons in get_items(store['Gamepad']['ButtonsPressed']):
                    if held_buttons:
                        try:
                            frame_data['GamepadButtonHeld'].add(held_buttons)
                        except KeyError:
                            frame_data['GamepadButtonHeld'] = set(held_buttons)
                
                #Cleanup disconnected controllers
                for id in invalid_ids:
                    del gamepads[id]
                    del store['Gamepad']['ButtonsPressed'][id]
                        
                if buttons_held:
                    try:
                        frame_data['GamepadButtonPress'] += buttons_held
                    except KeyError:
                        frame_data['GamepadButtonPress'] = buttons_held
                    store['LastActivity'] = ticks
                    for id, buttons in get_items(buttons_held):
                        NOTIFY(GAMEPAD_BUTTON_HELD, id, buttons)
                    
                if _buttons_pressed:
                    store['LastActivity'] = ticks
                    for id, buttons in get_items(_buttons_pressed):
                        NOTIFY(GAMEPAD_BUTTON_PRESS, id, buttons)
                    
                if _buttons_released:
                    store['LastActivity'] = ticks
                    for id, buttons in get_items(_buttons_released):
                        NOTIFY(GAMEPAD_BUTTON_RELEASED, id, buttons)
                
                
                #Resolution
                recalculate_mouse = False
                check_resolution = timer['UpdateScreen'] and not ticks % timer['UpdateScreen']
                
                #Check if resolution has changed
                if check_resolution:
                
                    if MULTI_MONITOR:
                        old_resolution = store['Resolution']['Boundaries']
                        store['Resolution']['Boundaries'] = monitor_info()
                        if old_resolution != store['Resolution']['Boundaries']:
                            frame_data['MonitorLimits'] = store['Resolution']['Boundaries']
                            recalculate_mouse = True
                    else:
                        store['Resolution']['Current'] = monitor_info()
                        if store['Resolution']['Previous'] != store['Resolution']['Current']:
                            if store['Resolution']['Previous'] is not None:
                                NOTIFY(RESOLUTION_CHANGED, store['Resolution']['Previous'], store['Resolution']['Current'])
                            frame_data['Resolution'] = store['Resolution']['Current']
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
                            #Calculate which monitor the mouse is on
                            try:
                                current_screen_resolution = monitor_offset(current_mouse_pos, store['Resolution']['Boundaries'])[0]
                            
                            except TypeError:
                            
                                if check_resolution:
                                    raise TypeError
                                    
                                #Send to background process if the monitor list changes
                                old_resolution = store['Resolution']['Boundaries']
                                store['Resolution']['Boundaries'] = monitor_info()
                                if old_resolution != store['Resolution']['Boundaries']:
                                    frame_data['MonitorLimits'] = store['Resolution']['Boundaries']
                                current_screen_resolution = monitor_offset(current_mouse_pos, store['Resolution']['Boundaries'])[0]
                        
                        except TypeError:
                            pass
                            
                        else:
                            if current_screen_resolution != store['Resolution']['Previous']:
                                if store['Resolution']['Previous'] is not None:
                                    NOTIFY(MONITOR_CHANGED, store['Resolution']['Previous'], current_screen_resolution)
                                store['Resolution']['Previous'] = current_screen_resolution
                
                
                #Send request to check history list
                if timer['HistoryCheck'] and not ticks % timer['HistoryCheck']:
                    frame_data['HistoryCheck'] = True
                            
                #Send request to update programs
                if timer['UpdatePrograms'] and not ticks % timer['UpdatePrograms']:
                    frame_data_rp['Update'] = True
                
                #Send request to reload program list
                if timer['ReloadProgramList'] and not ticks % timer['ReloadProgramList']:
                    frame_data_rp['Reload'] = True

                #Update user about the queue size
                if (timer['UpdateQueuedCommands'] and not ticks % timer['UpdateQueuedCommands'] 
                        and timer['Save'] and store['LastActivity'] > ticks - timer['Save']):
                    try:
                        NOTIFY(QUEUE_SIZE, q_bg_send.qsize())
                    except NotImplementedError:
                        pass
                
                #Send save request
                if store['Save']['Finished'] and ticks and not ticks % store['Save']['Next']:
                    frame_data['Save'] = True
                    store['Save']['Finished'] = False

                if store['Mouse']['OffScreen']:
                    mouse_pos['Previous'] = None
                else:
                    mouse_pos['Previous'] = mouse_pos['Current']
                ticks += 1
            
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
        message(u'{} {}'.format(time_format(time.time()), NOTIFY.get_output()))
        handle_error()
