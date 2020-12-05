"""This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""
#Foreground process for the main tracking
#Runs in realtime at 60 updates per second by default

from __future__ import division, absolute_import

import time
import traceback
from multiprocessing import Process, Queue
from threading import Thread

from .background import background_process, running_processes, monitor_offset, _notify_queue_size
from .xinput import Gamepad
from ..api import *
from ..misc import format_file_path
from ..config.settings import CONFIG
from ..config.language import LANGUAGE
from ..constants import UPDATES_PER_SECOND, DEFAULT_PATH
from ..error import handle_error
from ..files import Lock
from ..messages import time_format
from ..notify import NOTIFY
from ..utils.compatibility import Message, MessageWithQueue, iteritems
from ..utils.os import monitor_info, get_cursor_pos, get_mouse_click, get_key_press, MULTI_MONITOR, get_double_click_time
from ..utils.sockets import get_free_port


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


class PrintFormat(object):
    def __init__(self, message_object):
        self.message = message_object

    def __call__(self, text, current_time=None):
        if not text:
            return
        if current_time is None:
            current_time = time.time()
        self.message('{} {}'.format(time_format(current_time), text))


def track(lock=True, web_port=None, message_port=None, console=True, server_secret=None):
    """Put a lock on the main script to stop more than one instance running."""

    #Attempt to run the tracking script, with or without a lock
    error = None
    if lock:
        with Lock() as locked:
            if locked:
                error, web_port = _track(web_port=web_port, message_port=message_port, server_secret=server_secret)
            else:
                handle_error(LANGUAGE.strings['Tracking']['ScriptDuplicate'], log=False, console=console)
    else:
        error, web_port = _track(web_port=web_port, message_port=message_port, server_secret=server_secret)

    if error:
        if web_port is not None:
            shutdown_server(web_port)
        handle_error(error, console=console)


def _track(web_port=None, message_port=None, server_secret=None):

    _background_process = None
    no_detection_wait = 2

    try:
        q_feedback = Queue()

        #Setup message server
        if CONFIG['API']['SocketServer']:
            q_msg = Queue()
            message = PrintFormat(MessageWithQueue(q_msg).send)
            if message_port is None:
                message_port = get_free_port()
            message_thread = local_message_server(port=message_port, q_main=q_msg, q_feedback=q_feedback, server_secret=server_secret)
        else:
            message = PrintFormat(Message)
            message_port = None
            message_thread = None

        #Setup web server
        if CONFIG['API']['WebServer']:
            app.config.update(create_pipe('REQUEST', duplex=False))
            app.config.update(create_pipe('CONTROL', duplex=False))
            app.config.update(create_pipe('STATUS', duplex=False))
            app.config.update(create_pipe('PORT', duplex=False))
            app.config.update(create_pipe('CONFIG', duplex=False))
            app.config.update(create_pipe('CONFIG_UPDATE', duplex=False))
            if web_port is None:
                web_port = get_free_port()
            local_web_server(app=app, port=web_port, q_feedback=q_feedback)
        else:
            web_port = None
        message(NOTIFY.output())

        #Start main script
        message(NOTIFY(LANGUAGE.strings['Tracking']['ScriptPath'], DOCUMENTS_PATH=format_file_path(DEFAULT_PATH)).output())

        #Adjust timings to account for tick rate
        timer = {'UpdateScreen': CONFIG['Advanced']['CheckResolution'],
                 'UpdatePrograms': CONFIG['Advanced']['CheckRunningApplications'],
                 'Save': CONFIG['Save']['Frequency'] * UPDATES_PER_SECOND,
                 'ReloadProgramList': CONFIG['Advanced']['ReloadApplicationList'],
                 'UpdateQueuedCommands': CONFIG['Advanced']['ShowQueuedCommands'],
                 'RefreshGamepads': CONFIG['Advanced']['RefreshGamepads'],
                 'HistoryCheck': CONFIG['Advanced']['HistoryCheck'],
                 'API': CONFIG['Advanced']['APIPollingRate']}

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
                 'Keyboard': {'KeysPressed': {int(k): False for k in LANGUAGE.strings['Keys'].keys()},
                              'KeysInvalid': set()},
                 'LastActivity': 0,
                 'LastSent': 0,
                 'Save': {'Finished': True,
                          'Next': timer['Save']},
                 'Gamepad': {'ButtonsPressed': {}},
                 'Flask': {'App': app if web_port is not None else None,
                           'Port': {'Web': web_port,
                                    'Message': message_port}}
                }
        mouse_pos = store['Mouse']['Position']
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
        message(NOTIFY(LANGUAGE.strings['Tracking']['ScriptMainStart']).output())
        script_status = STATUS_RUNNING
        while script_status != STATUS_TERMINATED:
            with RefreshRateLimiter(UPDATES_PER_SECOND) as limiter:

                #Handle web server API requests
                if store['Flask']['App'] is not None and not ticks % timer['API']:

                    #Control state of script
                    if store['Flask']['App'].config['PIPE_CONTROL_RECV'].poll():
                        api_control = store['Flask']['App'].config['PIPE_CONTROL_RECV'].recv()

                        #Change if running or paused, or exit script
                        if api_control in (STATUS_RUNNING, STATUS_PAUSED, STATUS_TERMINATED):
                            script_status = api_control
                            options = {STATUS_RUNNING: LANGUAGE.strings['Tracking']['ScriptResume'],
                                       STATUS_PAUSED: LANGUAGE.strings['Tracking']['ScriptPause'],
                                       STATUS_TERMINATED: LANGUAGE.strings['Tracking']['ScriptStop']}
                            NOTIFY(options[script_status])

                        #Set config values
                        if api_control == CONFIG_SET:
                            config_header, config_var, config_val = store['Flask']['App'].config['PIPE_CONFIG_UPDATE_RECV'].recv()
                            CONFIG[config_header][config_var] = config_val
                            print('Set {}.{} to {}'.format(config_header, config_var, CONFIG[config_header][config_var]))

                        #Send request to close clients
                        elif api_control == CLOSE_MESSAGE_CONNECTIONS:
                            if message_thread is not None:
                                message_thread.force_close_clients = True

                    #Requests that require response
                    if store['Flask']['App'].config['PIPE_REQUEST_RECV'].poll():
                        request_id = store['Flask']['App'].config['PIPE_REQUEST_RECV'].recv()
                        if request_id == FEEDBACK_STATUS:
                            store['Flask']['App'].config['PIPE_STATUS_SEND'].send(script_status)
                        elif request_id == FEEDBACK_PORT:
                            store['Flask']['App'].config['PIPE_PORT_SEND'].send({'message': store['Flask']['Port']['Message'],
                                                                                 'web': store['Flask']['Port']['Web']})
                        elif request_id == FEEDBACK_CONFIG:
                            store['Flask']['App'].config['PIPE_CONFIG_SEND'].send(CONFIG)

                #Send data to thread
                try:
                    if frame_data or frame_data_rp:
                        last_sent = ticks - store['LastSent']
                        frame_data['Ticks'] = {'Total': last_sent,
                                               'Idle': ticks - store['LastActivity']}
                        if frame_data:
                            q_bg_send.put(frame_data)
                        if frame_data_rp:
                            q_rp_send.put(frame_data_rp)
                        store['LastSent'] = ticks
                except NameError:
                    pass

                #Get messages from running program thread
                while not q_rp_recv.empty():
                    received_message = q_rp_recv.get()

                    #End if exception was raised
                    try:
                        if received_message.startswith('Traceback (most recent call last)'):
                            q_bg_send.put({'Quit': True})
                            return received_message, store['Flask']['Port']['Web']

                    #Do not continue tracking held down keys after profile switch
                    except AttributeError:
                        if isinstance(received_message, dict):
                            if 'Program' in received_message:
                                store['Keyboard']['KeysInvalid'] |= set([k for k, v in iteritems(store['Keyboard']['KeysPressed']) if v])

                    #Print messages from thread
                    else:
                        message(received_message, limiter.time)

                #Print any messages from previous loop
                received_data = []
                while not q_bg_recv.empty():

                    received_message = q_bg_recv.get()

                    #Receive text messages, quit if exception
                    try:
                        if received_message.startswith('Traceback (most recent call last)'):
                            q_bg_send.put({'Quit': True})
                            return received_message, store['Flask']['Port']['Web']
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

                output_list = [received_data] + list(NOTIFY)

                #Add output from server
                if CONFIG['API']['SocketServer']:
                    received_data = []
                    while not q_feedback.empty():
                        received_data.append(q_feedback.get())
                    output_list.append(received_data)

                #Join all valid outputs together
                output = ' | '.join(' | '.join(msg_group) if isinstance(msg_group, (list, tuple)) else msg_group
                                    for msg_group in output_list if msg_group)
                if output:
                    message(output, limiter.time)

                #Break if script is not running
                #Below here is all the tracking
                if script_status != STATUS_RUNNING:
                    continue

                frame_data = {}
                frame_data_rp = {}

                #Mouse Movement
                mouse_pos['Current'] = get_cursor_pos()

                #Check if mouse is inactive (such as in a screensaver)
                if mouse_pos['Current'] is None:
                    if not store['Mouse']['Inactive']:
                        NOTIFY(LANGUAGE.strings['Tracking']['MouseUndetected'])
                        store['Mouse']['Inactive'] = True
                    time.sleep(no_detection_wait)
                    continue

                #Check if mouse left the monitor
                elif (not MULTI_MONITOR
                      and (not 0 <= mouse_pos['Current'][0] < store['Resolution']['Current'][0]
                           or not 0 <= mouse_pos['Current'][1] < store['Resolution']['Current'][1])):
                    if not store['Mouse']['OffScreen']:
                        NOTIFY(LANGUAGE.strings['Tracking']['MouseInvisible'])
                        store['Mouse']['OffScreen'] = True
                elif store['Mouse']['OffScreen']:
                    NOTIFY(LANGUAGE.strings['Tracking']['MouseVisible'])
                    store['Mouse']['OffScreen'] = False

                #Notify once if mouse is no longer inactive
                if store['Mouse']['Inactive']:
                    store['Mouse']['Inactive'] = False
                    NOTIFY(LANGUAGE.strings['Tracking']['MouseDetected'])

                #Check if mouse is in a duplicate position
                if mouse_pos['Current'] is None or mouse_pos['Current'] == mouse_pos['Previous']:
                    store['Mouse']['NotMoved'] += 1
                elif store['Mouse']['NotMoved']:
                    store['Mouse']['NotMoved'] = 0
                if not store['Mouse']['NotMoved']:
                    if not store['Mouse']['OffScreen']:
                        frame_data['MouseMove'] = [mouse_pos['Previous'], mouse_pos['Current'], []]
                        NOTIFY(LANGUAGE.strings['Tracking']['MousePosition'], XPOS=mouse_pos['Current'][0], YPOS=mouse_pos['Current'][1])
                        store['LastActivity'] = ticks


                #Mouse clicks
                click_repeat = CONFIG['Advanced']['RepeatClicks']
                for mouse_button, clicked in enumerate(get_mouse_click()):

                    mb_clicked = store['Mouse']['Clicked'].get(mouse_button, False)
                    mb_data = (mouse_button, mouse_pos['Current'])

                    _mb = LANGUAGE.strings['Mouse'][['ButtonLeft', 'ButtonMiddle', 'ButtonRight'][mouse_button]]
                    _click_type = LANGUAGE.strings['Mouse']['ClickSingle']

                    if clicked:
                        store['LastActivity'] = ticks

                        #Add any click events to the mouse move data
                        try:
                            frame_data['MouseMove'][2].append(mouse_button)
                        except KeyError:
                            pass

                        #First click
                        if not mb_clicked:

                            #Double click
                            double_click = False
                            if (store['Mouse']['LastClickTime'] > ticks - store['Mouse']['DoubleClickTime']
                                    and store['Mouse']['LastClick'] == mb_data):
                                store['Mouse']['LastClickTime'] = 0
                                store['Mouse']['LastClick'] = None
                                double_click = True
                                _ck = LANGUAGE.strings['Mouse']['ClickDouble']
                                try:
                                    frame_data['DoubleClick'].append(mb_data)
                                except KeyError:
                                    frame_data['DoubleClick'] = [mb_data]
                            else:
                                store['Mouse']['LastClickTime'] = ticks

                            #Single click
                            store['Mouse']['Clicked'][mouse_button] = ticks

                            if not store['Mouse']['OffScreen']:
                                NOTIFY(LANGUAGE.strings['Tracking']['MouseClickedVisible'],  MOUSEBUTTON=_mb, CLICKED=_click_type,
                                       XPOS=mouse_pos['Current'][0], YPOS=mouse_pos['Current'][1])
                                try:
                                    frame_data['MouseClick'].append(mb_data)
                                except KeyError:
                                    frame_data['MouseClick'] = [mb_data]
                                    frame_data['MouseHeld'] = False
                            else:
                                NOTIFY(LANGUAGE.strings['Tracking']['MouseClickedInvsible'], MOUSEBUTTON=_mb, CLICKED=_click_type)

                        #Held clicks
                        elif click_repeat and mb_clicked < ticks - click_repeat:
                            store['Mouse']['Clicked'][mouse_button] = ticks
                            if not store['Mouse']['OffScreen']:
                                NOTIFY(LANGUAGE.strings['Tracking']['MouseHeldVisible'], MOUSEBUTTON=_mb, CLICKED=_click_type,
                                       XPOS=mouse_pos['Current'][0], YPOS=mouse_pos['Current'][1])
                                try:
                                    frame_data['MouseClick'].append(mb_data)
                                except KeyError:
                                    frame_data['MouseClick'] = [mb_data]
                                frame_data['MouseHeld'] = True
                            else:
                                NOTIFY(LANGUAGE.strings['Tracking']['MouseHeldInvsible'], MOUSEBUTTON=_mb, CLICKED=_click_type)

                        store['Mouse']['LastClick'] = mb_data

                    elif mb_clicked:
                        NOTIFY(LANGUAGE.strings['Tracking']['MouseClickedRelease'], MOUSEBUTTON=_mb)
                        del store['Mouse']['Clicked'][mouse_button]
                        store['LastActivity'] = ticks

                #Key presses
                keys_pressed = []
                keys_held = []
                key_status = store['Keyboard']['KeysPressed']
                key_press_repeat = CONFIG['Advanced']['RepeatKeyPress']
                key_invalid = store['Keyboard']['KeysInvalid']
                _keys_held = []
                _keys_pressed = []
                _keys_released = []

                for key_int, key_name in iteritems(LANGUAGE.strings['Keys']):
                    key_int = int(key_int)
                    if get_key_press(key_int):

                        #Ignore if held down from last profile
                        if key_int in key_invalid:
                            continue

                        keys_held.append(key_int)

                        #If key is currently being held down
                        if key_status[key_int]:
                            if key_press_repeat and key_status[key_int] < ticks - key_press_repeat:
                                keys_pressed.append(key_int)
                                _keys_held.append(key_name)
                                key_status[key_int] = ticks

                        #If key has been pressed
                        else:
                            keys_pressed.append(key_int)
                            _keys_pressed.append(key_name)
                            key_status[key_int] = ticks

                    #If key has been released
                    elif key_status[key_int]:
                        key_status[key_int] = False
                        _keys_released.append(key_name)

                        #Mark key as valid again
                        try:
                            key_invalid.remove(key_int)
                        except KeyError:
                            pass

                if keys_pressed:
                    frame_data['KeyPress'] = keys_pressed
                    store['LastActivity'] = ticks

                if keys_held:
                    frame_data['KeyHeld'] = keys_held
                    store['LastActivity'] = ticks

                if _keys_pressed or _keys_held or _keys_released:
                    if _keys_pressed:
                        plural = len(_keys_pressed) != 1
                        NOTIFY(LANGUAGE.strings['Tracking']['KeyboardPressed'], KEYS=', '.join(_keys_pressed),
                                       KEY_PLURAL=LANGUAGE.strings['Words'][('KeyboardKeySingle', 'KeyboardKeyPlural')[plural]],
                                       PRESS_PLURAL=LANGUAGE.strings['Words'][('PressSingle', 'PressPlural')[plural]])

                    if _keys_held:
                        plural = len(_keys_held) != 1
                        NOTIFY(LANGUAGE.strings['Tracking']['KeyboardHeld'], KEYS=', '.join(_keys_held),
                               KEY_PLURAL=LANGUAGE.strings['Words'][('KeyboardKeySingle', 'KeyboardKeyPlural')[plural]],
                               PRESS_PLURAL=LANGUAGE.strings['Words'][('PressSingle', 'PressPlural')[plural]])

                    if _keys_released:
                        plural = len(_keys_released) != 1
                        NOTIFY(LANGUAGE.strings['Tracking']['KeyboardReleased'], KEYS=', '.join(_keys_released),
                               KEY_PLURAL=LANGUAGE.strings['Words'][('KeyboardKeySingle', 'KeyboardKeyPlural')[plural]],
                               RELEASE_PLURAL=LANGUAGE.strings['Words'][('ReleaseSingle', 'ReleasePlural')[plural]])


                if CONFIG['Main']['_TrackGamepads']:
                    #Reload list of gamepads (in case one was plugged in)
                    if timer['RefreshGamepads'] and not ticks % timer['RefreshGamepads']:
                        try:
                            old_gamepads = set(gamepads)
                        except UnboundLocalError:
                            old_gamepads = set()
                        gamepads = {gamepad.device_number: gamepad for gamepad in Gamepad.list_gamepads()}
                        difference = set(gamepads) - old_gamepads
                        for i, id in enumerate(difference):
                            NOTIFY(LANGUAGE.strings['Tracking']['GamepadConnected'], ID=id)
                            store['Gamepad']['ButtonsPressed'][id] = {}

                    #Gamepad tracking (multiple controllers not tested yet)
                    button_repeat = CONFIG['Advanced']['RepeatButtonPress']
                    invalid_ids = []
                    buttons_held = {}
                    _buttons_pressed = {}
                    _buttons_released = {}

                    for id, gamepad in iteritems(gamepads):

                        #Repeat presses
                        if button_repeat:
                            for button_id, last_update in iteritems(store['Gamepad']['ButtonsPressed'][id]):
                                if last_update < ticks - button_repeat:
                                    try:
                                        buttons_held[id].append(button_id)
                                    except KeyError:
                                        buttons_held[id] = [button_id]
                                    store['Gamepad']['ButtonsPressed'][id][button_id] = ticks

                        with gamepad as gamepad_input:

                            #Break the connection if controller can't be found
                            if not gamepad.connected:
                                NOTIFY(LANGUAGE.strings['Tracking']['GamepadDisconnected'], ID=id)
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
                                for axis, value in iteritems(printable):
                                    NOTIFY(LANGUAGE.strings['Tracking']['GamepadAxis'], ID=id, AXIS=axis, VALUE=value)

                            #Button events
                            button_presses = gamepad_input.get_button()
                            if button_presses:
                                for button_id, state in iteritems(button_presses):

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
                    for id, held_buttons in iteritems(store['Gamepad']['ButtonsPressed']):
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
                        for id, buttons in iteritems(buttons_held):
                            NOTIFY(LANGUAGE.strings['Tracking']['GamepadButtonHeld'], ID=id, BUTTONS=', '.join(map(str, buttons)),
                                   BUTTON_PLURAL=LANGUAGE.strings['Words'][('GamepadButtonSingle', 'GamepadButtonPlural')[len(buttons) != 1]])

                    if _buttons_pressed:
                        store['LastActivity'] = ticks
                        for id, buttons in iteritems(_buttons_pressed):
                            NOTIFY(LANGUAGE.strings['Tracking']['GamepadButtonPressed'], ID=id, BUTTONS=', '.join(map(str, buttons)),
                                   BUTTON_PLURAL=LANGUAGE.strings['Words'][('GamepadButtonSingle', 'GamepadButtonPlural')[len(buttons) != 1]])

                    if _buttons_released:
                        store['LastActivity'] = ticks
                        for id, buttons in iteritems(_buttons_released):
                            NOTIFY(LANGUAGE.strings['Tracking']['GamepadButtonReleased'], ID=id, BUTTONS=', '.join(map(str, buttons)),
                                   BUTTON_PLURAL=LANGUAGE.strings['Words'][('GamepadButtonSingle', 'GamepadButtonPlural')[len(buttons) != 1]])


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
                                NOTIFY(LANGUAGE.strings['Tracking']['ResolutionNew'],
                                       XRES_OLD=store['Resolution']['Previous'][0], YRES_OLD=store['Resolution']['Previous'][1],
                                       XRES=store['Resolution']['Current'][0], YRES=store['Resolution']['Current'][0])
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
                                    raise

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
                                    NOTIFY(LANGUAGE.strings['Tracking']['ResolutionChanged'],
                                           XRES_OLD=store['Resolution']['Previous'][0], YRES_OLD=store['Resolution']['Previous'][1],
                                           XRES=current_screen_resolution[0], YRES=current_screen_resolution[1])
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
                    _notify_queue_size(q_bg_send)

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
        traceback_message = traceback.format_exc()
        if _background_process is not None:
            try:
                q_bg_send.put({'Quit': True})
            except IOError:
                pass
        try:
            web_port = store['Flask']['Port']['Web']
        except UnboundLocalError:
            web_port = None
        return traceback_message, web_port

    except KeyboardInterrupt:
        if _background_process is not None:
            try:
                q_bg_send.put({'Quit': True})
            except IOError:
                pass
        NOTIFY(LANGUAGE.strings['Tracking']['ScriptThreadEnd'])
        NOTIFY(LANGUAGE.strings['Tracking']['ScriptMainEnd'])
        message(NOTIFY.output())

    #The web port is always returned so set it even if the script failed
    try:
        web_port = store['Flask']['Port']['Web']
    except UnboundLocalError:
        web_port = None
    return None, web_port