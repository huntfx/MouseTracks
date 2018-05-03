"""
This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""
#The background process does all the heavy lifting and is not required to be in realtime

from __future__ import division, absolute_import

from collections import defaultdict
import time
import traceback

import core.numpy as numpy
from core.applications import RunningApplications
from core.compatibility import range, iteritems
from core.config import CONFIG
from core.constants import MAX_INT, TRACKING_DISABLE, TRACKING_IGNORE, UPDATES_PER_SECOND, KEY_STATS, DEFAULT_NAME
from core.files import LoadData, save_data, prepare_file
from core.language import STRINGS
from core.maths import find_distance, calculate_line, round_int
from core.notify import NOTIFY
from core.os import MULTI_MONITOR, monitor_info, set_priority
    

def running_processes(q_recv, q_send, background_send):
    """Check for running processes.
    As refreshing the list takes some time but not CPU, this is put in its own thread
    and sends the currently running program to the backgrund process.
    """
    try:
        previous_app = None
        last_coordinates = None
        last_resolution = None
        
        NOTIFY(STRINGS['Tracking']['ApplicationListen']).put(q_send)

        while True:
                
            received_data = q_recv.get()

            if 'Reload' in received_data:
                try:
                    running_apps.reload_file()
                except (NameError, UnboundLocalError):
                    running_apps = RunningApplications(queue=q_send)
                
                NOTIFY(STRINGS['Tracking']['AppListReload'], FILE_NAME=running_apps.applist.name)

            if 'Update' in received_data:
                running_apps.refresh()
                
                current_app = running_apps.check()
                send = {}
                
                if current_app is not None and current_app[0] == TRACKING_IGNORE:
                    current_app = None
                
                #Send custom resolution
                if running_apps.focus is not None:
                    
                    if current_app is None:
                        app_resolution = None
                    
                    else:
                        app_resolution = (running_apps.focus.rect, running_apps.focus.resolution)
                        
                        if current_app == previous_app:
                            if app_resolution[1] != last_resolution:
                                NOTIFY(STRINGS['Tracking']['ResolutionAppResize'],
                                       XRES_OLD=last_resolution[0], YRES_OLD=last_resolution[1],
                                       XRES=app_resolution[1][0], YRES=app_resolution[1][1])
                            elif app_resolution[0] != last_coordinates:
                                NOTIFY(STRINGS['Tracking']['ResolutionAppMove'],
                                       XRES_OLD=last_coordinates[0], YRES_OLD=last_coordinates[1],
                                       XRES=app_resolution[0][0], YRES=app_resolution[0][1])
                        else:
                            NOTIFY(STRINGS['Tracking']['ResolutionAppLoad'], 
                                   XRES=app_resolution[1][0], YRES=app_resolution[1][1])
                            
                        last_coordinates, last_resolution = app_resolution
                
                #Detect running program
                if current_app != previous_app:
                    
                    if running_apps.focus is None:
                        send['ApplicationResolution'] = None
                        app_start = STRINGS['Tracking']['ApplicationStart']
                        app_end = STRINGS['Tracking']['ApplicationEnd']
                    else:
                        app_start = STRINGS['Tracking']['ApplicationFocused']
                        app_end = STRINGS['Tracking']['ApplicationUnfocused']
                
                    process_id = None
                    if current_app is None:
                        NOTIFY(app_end, APPLICATION_NAME=previous_app[0])
                    else:
                        if running_apps.focus is not None:
                            if previous_app is not None:
                                NOTIFY(app_end, APPLICATION_NAME=previous_app[0])
                            process_id = running_apps.focus.pid
                        NOTIFY(app_start, APPLICATION_NAME=current_app[0])
                        
                    NOTIFY.put(q_send)
                    send['Program'] = (process_id, current_app)
                    
                    previous_app = current_app
                
                if send:
                    background_send.put(send)
                    q_send.put(send)
    
    #Catch error after KeyboardInterrupt
    except EOFError:
        return
    
    except Exception:
        q_send.put(traceback.format_exc())


def _save_wrapper(q_send, program_name, data, new_program=False):
    """Handle saving the data files from the thread."""
    
    if program_name is not None and program_name[0] == TRACKING_DISABLE:
        return
    
    NOTIFY(STRINGS['Tracking']['SavePrepare']).put(q_send)
    saved = False

    #Get how many attempts to use
    if new_program:
        max_attempts = CONFIG['Save']['MaximumAttemptsSwitch']
    else:
        max_attempts = CONFIG['Save']['MaximumAttemptsNormal']
    
    compressed_data = prepare_file(data)
    
    #Attempt to save
    NOTIFY(STRINGS['Tracking']['SaveStart']).put(q_send)
    for i in range(max_attempts):
        if save_data(program_name, compressed_data, _compress=False):
            NOTIFY(STRINGS['Tracking']['SaveComplete']).put(q_send)
            saved = True
            break
        
        else:
            if max_attempts == 1:
                NOTIFY(STRINGS['Tracking']['SaveIncompleteNoRetry'])
                return

            seconds = round_int(CONFIG['Save']['WaitAfterFail'])
            minutes = round_int(CONFIG['Save']['WaitAfterFail'] / 60)
            NOTIFY(STRINGS['Tracking']['SaveIncompleteRetry'], ATTEMPT_CURRENT=i+1, ATTEMPT_MAX=max_attempts,
                   SECONDS=seconds, SECONDS_PLURAL=STRINGS['Words'][('TimeSecondSingle', 'TimeSecondPlural')[seconds != 1]],
                   MINUTES=minutes, MINUTES_PLURAL=STRINGS['Words'][('TimeMinuteSingle', 'TimeMinutePlural')[minutes != 1]])

            time.sleep(CONFIG['Save']['WaitAfterFail'])
            
    if not saved:
        NOTIFY(STRINGS['Tracking']['SaveIncompleteRetryFail'])


def _notify_queue_size(queue_main, queue_send=None):
    """Add number of queued commands to Notify class."""
    try:
        remaining_commands = queue_main.qsize()
    except NotImplementedError:
        return
    NOTIFY(STRINGS['Tracking']['ScriptQueueSize'], NUMBER=remaining_commands, 
            COMMANDS_PLURAL=STRINGS['Words'][('CommandSingle', 'CommandPlural')[remaining_commands != 1]]).put(queue_send)


def background_process(q_recv, q_send):
    """Function to handle all the data from the main thread."""
    try:
        NOTIFY(STRINGS['Tracking']['ScriptThreadStart']).put(q_send)
        set_priority('low')
        
        store = {'Data': LoadData(),
                 'LastProgram': None,
                 'Resolution': None,
                 'MonitorLimits': None,
                 'Offset': (0, 0),
                 'LastResolution': None,
                 'ActivitySinceLastSave': False,
                 'SavesSkipped': 0,
                 'ApplicationResolution': None,
                 'LastClick': None,
                 'KeyTrack': {'LastKey': None,
                              'Time': None,
                              'Backspace': False},
                 'FirstLoad': True,
                 'LastTrackUpdate': 0,
                 'LastIdle': 0,
                 'ProcessIDs': defaultdict(set)
                }
        
        NOTIFY(STRINGS['Tracking']['ProfileLoad'])
        _notify_queue_size(q_recv)
        NOTIFY.put(q_send)
        
        while True:
            received_data = q_recv.get()
            
            #Increment the amount of time the script has been running for
            if 'Ticks' in received_data:
                store['Data']['Ticks']['Total'] += received_data['Ticks']['Total']
                store['Data']['Sessions'][-1][1] += received_data['Ticks']['Total']
                
                #Increment idle time if it reaches a threshold (>10 seconds)
                #TODO: Set idle time in config
                if store['LastIdle'] > received_data['Ticks']['Idle'] and store['LastIdle'] > UPDATES_PER_SECOND * 10:
                    store['Data']['Sessions'][-1][2] += store['LastIdle']
                store['LastIdle'] = received_data['Ticks']['Idle']
            
            #Save the data
            if 'Save' in received_data:
                if store['ActivitySinceLastSave']:
                    _save_wrapper(q_send, store['LastProgram'], store['Data'], False)
                    store['ActivitySinceLastSave'] = False
                    store['SavesSkipped'] = 0
                    _notify_queue_size(q_recv)

                else:
                    store['SavesSkipped'] += 1
                    
                    #Say why the save was skipped
                    try:
                        queue_size = q_recv.qsize()
                    except NotImplementedError:
                        queue_size = 0
                    if queue_size > 2:
                        NOTIFY(STRINGS['Tracking']['SaveSkipNoChange'])
                    else:
                        time_since_save = CONFIG['Save']['Frequency'] * store['SavesSkipped']
                        seconds = int(time_since_save)
                        minutes = int(round(time_since_save / 60))
                        hours = int(round(time_since_save / 3600))
                        seconds_plural = STRINGS['Words'][('TimeSecondSingle', 'TimeSecondPlural')[seconds != 1]]
                        minutes_plural = STRINGS['Words'][('TimeMinuteSingle', 'TimeMinutePlural')[minutes != 1]]
                        hours_plural = STRINGS['Words'][('TimeHourSingle', 'TimeHourPlural')[hours != 1]]
                        NOTIFY(STRINGS['Tracking']['SaveSkipInactivity'], 
                               SECONDS=seconds, SECONDS_PLURAL=seconds_plural,
                               MINUTES=minutes, MINUTES_PLURAL=minutes_plural,
                               HOURS=hours, HOURS_PLURAL=hours_plural)
                q_send.put({'SaveFinished': None})
            
            update_resolution = False
            
            #Check for new program loaded
            if 'Program' in received_data:
                process_id, current_program = received_data['Program']
                
                if current_program != store['LastProgram']:
                    update_resolution = True
                    
                    _program_name = current_program[0] if current_program is not None else DEFAULT_NAME
                    NOTIFY(STRINGS['Tracking']['ApplicationLoad'], APPLICATION_NAME=_program_name).put(q_send)

                    #Save old profile
                    _save_wrapper(q_send, store['LastProgram'], store['Data'], True)
                    
                    #Load new profile
                    allow_new_session = current_program is not None or current_program is None and store['LastProgram'] is None
                    try:
                        if process_id is not None and process_id in store['ProcessIDs'][current_program]:
                            allow_new_session = False
                    except KeyError:
                        pass
                    if process_id is not None:
                        store['ProcessIDs'][current_program].add(process_id)
                    store['Data'] = LoadData(current_program, _reset_sessions=allow_new_session)
                    store['LastProgram'] = current_program
                    store['ActivitySinceLastSave'] = False
                    
                    #Check new resolution
                    try:
                        store['ApplicationResolution'] = received_data['ApplicationResolution']
                    except KeyError:
                        pass
                    if store['ApplicationResolution'] is None:
                        check_resolution(store['Data'], store['Resolution'])
                    else:
                        check_resolution(store['Data'], store['ApplicationResolution'][1])
                        
                    if store['Data']['Ticks']['Total']:
                        NOTIFY(STRINGS['Tracking']['ProfileLoad'])
                    else:
                        NOTIFY(STRINGS['Tracking']['ProfileNew'])

                    _notify_queue_size(q_recv)
                NOTIFY.put(q_send)
            
            if 'ApplicationResolution' in received_data:
                store['ApplicationResolution'] = received_data['ApplicationResolution']
                if store['ApplicationResolution'] is not None:
                    check_resolution(store['Data'], store['ApplicationResolution'][1])
                    update_resolution = True

            if 'Resolution' in received_data:
                store['Resolution'] = received_data['Resolution']
                check_resolution(store['Data'], received_data['Resolution'])
                update_resolution = True
            
            if 'MonitorLimits' in received_data:
                store['MonitorLimits'] = received_data['MonitorLimits']
                update_resolution = True
            
            #Keep the history tracking the correct resolution
            if update_resolution and CONFIG['Main']['HistoryLength']:
                if store['ApplicationResolution'] is not None:
                    history_resolution = store['ApplicationResolution']
                elif MULTI_MONITOR:
                    history_resolution = store['MonitorLimits']
                else:
                    history_resolution = store['Resolution']
                try:
                    if store['Data']['HistoryAnimation']['Tracks'][-1][0] != history_resolution:
                        raise IndexError
                except IndexError:
                    store['Data']['HistoryAnimation']['Tracks'].append([history_resolution])
            
            #Record key presses
            if 'KeyPress' in received_data:
                store['ActivitySinceLastSave'] = True
                record_key_press(store, received_data['KeyPress'])
            
            #Record time keys are held down
            if 'KeyHeld' in received_data:
                record_key_held(store, received_data['KeyHeld'])
                store['ActivitySinceLastSave'] = True
            
            #Record button presses
            if 'GamepadButtonPress' in received_data:
                store['ActivitySinceLastSave'] = True
                record_gamepad_pressed(store, received_data['GamepadButtonPress'])
            
            #Record how long buttons are held
            if 'GamepadButtonHeld' in received_data:
                store['ActivitySinceLastSave'] = True
                record_gamepad_held(store, received_data['GamepadButtonHeld'])
                        
            #Axis updates
            if 'GamepadAxis' in received_data:
                record_gamepad_axis(store, received_data['GamepadAxis'])
                                
            
            #Calculate and track mouse movement
            if 'MouseMove' in received_data:
                store['ActivitySinceLastSave'] = True
                record_mouse_move(store, received_data['MouseMove'])
                
                #Add to history if set
                if CONFIG['Main']['HistoryLength']:
                    store['Data']['HistoryAnimation']['Tracks'][-1].append(received_data['MouseMove'][1])
                
                #Compress tracks if the count gets too high
                max_track_value = CONFIG['Advanced']['CompressTrackMax']
                if not max_track_value:
                    max_track_value = MAX_INT
                
                if store['Data']['Ticks']['Tracks'] > max_track_value:
                    NOTIFY(STRINGS['Tracking']['CompressStart'], TRACK_TYPE='tracks').put(q_send)
                    
                    compress_tracks(store, CONFIG['Advanced']['CompressTrackAmount'])
                    
                    NOTIFY(STRINGS['Tracking']['CompressEnd'], TRACK_TYPE='tracks')
                    _notify_queue_size(q_recv)
                
            #Record mouse clicks
            if 'MouseClick' in received_data:
                store['ActivitySinceLastSave'] = True
                record_click_single(store, received_data['MouseClick'])
                    
            #Record double clicks
            if 'DoubleClick' in received_data:
                store['ActivitySinceLastSave'] = True
                record_click_double(store, received_data['DoubleClick'])
            
            #Trim the history list if too long
            if 'HistoryCheck' in received_data:
                max_length = CONFIG['Main']['HistoryLength'] * UPDATES_PER_SECOND
                history_trim(store, max_length)
                        
            store['Data']['Ticks']['Recorded'] += 1
            
            if 'Quit' in received_data or 'Exit' in received_data:
                return

            NOTIFY.put(q_send)
        
        #Exit process (this shouldn't happen for now)
        NOTIFY(STRINGS['Tracking']['ScriptThreadEnd']).put(q_send)
        _save_wrapper(q_send, store['LastProgram'], store['Data'], False)
            
    except Exception as e:
        q_send.put(traceback.format_exc())
        
    except KeyboardInterrupt:
        pass
        
        
def check_resolution(data, resolution):
    """Make sure resolution exists in data."""
    if resolution is None:
        return
    if not isinstance(resolution, tuple):
        raise ValueError('incorrect resolution: {}'.format(resolution))
        
    #Add empty resolution maps
    if resolution not in data['Resolution']:
        data['Resolution'][resolution] = {'Tracks': numpy.array(resolution, create=True),
                                          'Speed': numpy.array(resolution, create=True),
                                          'Strokes': numpy.array(resolution, create=True),
                                          'StrokesSeparate': {'Left': numpy.array(resolution, create=True),
                                                              'Middle': numpy.array(resolution, create=True),
                                                              'Right': numpy.array(resolution, create=True)},
                                          'Clicks': {'Single': {'Left': numpy.array(resolution, create=True),
                                                                'Middle': numpy.array(resolution, create=True),
                                                                'Right': numpy.array(resolution, create=True)},
                                                     'Double': {'Left': numpy.array(resolution, create=True),
                                                                'Middle': numpy.array(resolution, create=True),
                                                                'Right': numpy.array(resolution, create=True)}}}

                                        
def monitor_offset(coordinate, monitor_limits):
    """Detect which monitor the mouse is currently over."""
    if coordinate is None:
        return
    mx, my = coordinate
    for x1, y1, x2, y2 in monitor_limits:
        if x1 <= mx < x2 and y1 <= my < y2:
            return ((x2 - x1, y2 - y1), (x1, y1))


def get_monitor_coordinate(x, y, store):
    """Find the resolution of the monitor and adjusted x, y coordinates."""

    if store['ApplicationResolution'] is not None:
        try:
            resolution, (x_offset, y_offset) = monitor_offset((x, y),  [store['ApplicationResolution'][0]])
        except TypeError:
            return None
            
        return ((x - x_offset, y - y_offset), resolution)
            
    elif MULTI_MONITOR:
    
        try:
            resolution, (x_offset, y_offset) = monitor_offset((x, y), store['MonitorLimits'])
        except TypeError:
            store['MonitorLimits'] = monitor_info()
            try:
                resolution, (x_offset, y_offset) = monitor_offset((x, y), store['MonitorLimits'])
            except TypeError:
                return None
        
        check_resolution(store['Data'], resolution)
        return ((x - x_offset, y - y_offset), resolution)
        
    else:
        resolution = store['Resolution']
        
        return ((x, y), resolution)
        

def history_trim(store, desired_length):
    """Trim the history animation to the desired length."""
    
    history = store['Data']['HistoryAnimation']['Tracks']
    
    #Delete all history
    if not desired_length:
        store['Data']['HistoryAnimation']['Tracks'] = [history[-1][0]]
        return True
    
    #No point checking if it's too long first, it will probably take just as long
    total = 0
    for count, items in enumerate(history[::-1]):
        total += len(items) - 1
        
        if total >= desired_length:
            
            #Cut off the earlier resolutions
            start_point = len(history) - count - 1
            history = history[start_point:]
            
            #Trim the first record if not exact
            if total > desired_length:
                history[0] = [history[0][0]] + history[0][total-desired_length+1:]
            
            store['Data']['HistoryAnimation']['Tracks'] = history
            return True
            
    return False


def _record_click(store, received_data, click_type):
    for mouse_button_index, (x, y) in received_data:
        
        try:
            (x, y), resolution = get_monitor_coordinate(x, y, store)
        except TypeError:
            continue
        
        mouse_button = ['Left', 'Middle', 'Right'][mouse_button_index]
        store['Data']['Resolution'][resolution]['Clicks'][click_type][mouse_button][y][x] += 1


def record_click_single(store, received_data):
    return _record_click(store, received_data, 'Single')


def record_click_double(store, received_data):
    return _record_click(store, received_data, 'Double')
    

def compress_tracks(store, multiplier):
    
    for resolution, maps in iteritems(store['Data']['Resolution']):
        maps['Tracks'] = numpy.divide(maps['Tracks'], multiplier, as_int=True)
        maps['StrokesSeparate']['Left'] = numpy.divide(maps['StrokesSeparate']['Left'], multiplier, as_int=True)
        maps['StrokesSeparate']['Middle'] = numpy.divide(maps['StrokesSeparate']['Middle'], multiplier, as_int=True)
        maps['StrokesSeparate']['Right'] = numpy.divide(maps['StrokesSeparate']['Right'], multiplier, as_int=True)
            
    store['Data']['Ticks']['Tracks'] //= multiplier
    store['Data']['Ticks']['Tracks'] = int(store['Data']['Ticks']['Tracks'])
    store['Data']['Ticks']['Session']['Tracks'] //= multiplier
    store['Data']['Ticks']['Session']['Tracks'] = int(store['Data']['Ticks']['Session']['Tracks'])
    
    
def _record_gamepad(store, received_data, press_type):
    for button_id in received_data:
        try:
            store['Data']['Gamepad']['All']['Buttons'][press_type][button_id] += 1
        except KeyError:
            store['Data']['Gamepad']['All']['Buttons'][press_type][button_id] = 1
        try:
            store['Data']['Gamepad']['Session']['Buttons'][press_type][button_id] += 1
        except KeyError:
            store['Data']['Gamepad']['Session']['Buttons'][press_type][button_id] = 1


def record_gamepad_pressed(store, received_data):
    return _record_gamepad(store, received_data, 'Pressed')
    

def record_gamepad_held(store, received_data):
    return _record_gamepad(store, received_data, 'Held')


def record_gamepad_axis(store, received_data):
        for controller_axis in received_data:
            for axis, amount in iteritems(controller_axis):
                try:
                    store['Data']['Gamepad']['All']['Axis'][axis][amount] += 1
                except KeyError:
                    try:
                        store['Data']['Gamepad']['All']['Axis'][axis][amount] = 1
                    except KeyError:
                        store['Data']['Gamepad']['All']['Axis'][axis] = {amount: 1}
                try:
                    store['Data']['Gamepad']['Session']['Axis'][axis][amount] += 1
                except KeyError:
                    try:
                        store['Data']['Gamepad']['Session']['Axis'][axis][amount] = 1
                    except KeyError:
                        store['Data']['Gamepad']['Session']['Axis'][axis] = {amount: 1}    


def _record_keypress(key_dict, *args):
    """Quick way of recording keypresses that doesn't involve a million try/excepts."""

    all = key_dict['All']
    session = key_dict['Session']
    
    for i in args[:-1]:
        try:
            all[i]
        except KeyError:
            all[i] = {}
        all = all[i]
        try:
            session[i]
        except KeyError:
            session[i] = {}
        session = session[i]
    
    try:
        all[args[-1]] += 1
    except KeyError:
        all[args[-1]] = 1
    try:
        session[args[-1]] += 1
    except KeyError:
        session[args[-1]] = 1


def record_key_press(store, received_data):
    for key in received_data:
    
        _record_keypress(store['Data']['Keys'], 'Pressed', key)
        
        if key not in KEY_STATS:
            store['KeyTrack']['LastKey'] = None
            
        else:
            #Record mistakes
            #Only records the key if a single backspace is used
            if key == 'BACK':
                last = store['KeyTrack']['LastKey']
                if last is not None and last != 'BACK':
                    store['KeyTrack']['Backspace'] = last
                else:
                    store['KeyTrack']['Backspace'] = False
            elif store['KeyTrack']['Backspace']:
                _record_keypress(store['Data']['Keys'], 'Mistakes', store['KeyTrack']['Backspace'], key)
                store['KeyTrack']['Backspace'] = False
            
            #Record interval between key presses
            CONFIG['Advanced']['KeypressIntervalMax'] = 60
            if store['KeyTrack']['Time'] is not None and store['KeyTrack']['LastKey'] is not None:
                time_difference = store['Data']['Ticks']['Total'] - store['KeyTrack']['Time']
                if CONFIG['Advanced']['KeypressIntervalMax'] < 0 or time_difference <= CONFIG['Advanced']['KeypressIntervalMax']:
                    _record_keypress(store['Data']['Keys'], 'Intervals', 'Total', time_difference)
                    _record_keypress(store['Data']['Keys'], 'Intervals', 'Individual', store['KeyTrack']['LastKey'], key, time_difference)
            store['KeyTrack']['LastKey'] = key
            store['KeyTrack']['Time'] = store['Data']['Ticks']['Total']
        

def record_key_held(store, received_data):
    for key in received_data:
        _record_keypress(store['Data']['Keys'], 'Held', key)
        
        
def record_mouse_move(store, received_data):

    store['ActivitySinceLastSave'] = True
    resolution = 0
    _resolution = -1
    
    start, end, clicked = received_data
    distance = find_distance(end, start)
    
    #Misc stats
    store['Data']['Distance']['Tracks'] += distance
    continuous = store['LastTrackUpdate'] + 1 == store['Data']['Ticks']['Total']
    
    #Calculate the pixels in the line
    if start is None:
        mouse_coordinates = [end]
    else:
        mouse_coordinates = [start] + calculate_line(start, end) + [end]
        
    #Make sure resolution exists in data
    if store['ApplicationResolution'] is not None:
        check_resolution(store['Data'], store['ApplicationResolution'][1])
        
    elif MULTI_MONITOR:
        try:
            #Don't bother calculating offset for each pixel
            #if both start and end are on the same monitor
            resolution, (x_offset, y_offset) = monitor_offset(start, store['MonitorLimits'])
            _resolution = monitor_offset(end, store['MonitorLimits'])[0]
        except TypeError:
            if not resolution:
                mouse_coordinates = []
        else:
            check_resolution(store['Data'], resolution)
            if resolution != _resolution:
                check_resolution(store['Data'], resolution)
            _resolutions = [resolution, _resolution]
    
    #Write each pixel to the dictionary
    for (x, y) in mouse_coordinates:
    
        try:
            (x, y), resolution = get_monitor_coordinate(x, y, store)
        except TypeError:
            continue
            
        store['Data']['Resolution'][resolution]['Tracks'][y][x] = store['Data']['Ticks']['Tracks']
        if continuous:
            old_value = store['Data']['Resolution'][resolution]['Speed'][y][x]
            store['Data']['Resolution'][resolution]['Speed'][y][x] = max(distance, old_value)
            if clicked:
                old_value = store['Data']['Resolution'][resolution]['Strokes'][y][x]
                store['Data']['Resolution'][resolution]['Strokes'][y][x] = max(distance, old_value)
            
            #Testing separate maps for strokes
            for mouse_button, click_type in enumerate(('Left', 'Middle', 'Right')):
                if mouse_button in clicked:
                    store['Data']['Resolution'][resolution]['StrokesSeparate'][click_type][y][x] = store['Data']['Ticks']['Tracks']
                else:
                    store['Data']['Resolution'][resolution]['StrokesSeparate'][click_type][y][x] = 0
    
    store['LastTrackUpdate'] = store['Data']['Ticks']['Total']
    store['Data']['Ticks']['Tracks'] += 1