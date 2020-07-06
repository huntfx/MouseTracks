"""This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""
#Background process for the main tracking
#Contains all the heavy lifting and is not processed in realtime

from __future__ import division, absolute_import

from collections import defaultdict
import time
import traceback

from ..utils import numpy
from ..applications import RunningApplications
from ..utils.compatibility import range, iteritems
from ..config.settings import CONFIG
from ..constants import MAX_INT, TRACKING_DISABLE, TRACKING_IGNORE, UPDATES_PER_SECOND, KEY_STATS, DEFAULT_NAME
from ..files import LoadData, save_data, prepare_file
from ..config.language import LANGUAGE
from ..utils.maths import find_distance, calculate_line, round_int
from ..notify import NOTIFY
from ..utils.os import MULTI_MONITOR, monitor_info, set_priority
    

def running_processes(q_recv, q_send, background_send):
    """Check for running processes.
    As refreshing the list takes some time but not CPU, this is put in its own thread
    and sends the currently running program to the backgrund process.
    """
    try:
        previous_app = None
        last_coordinates = None
        last_resolution = None
        
        NOTIFY(LANGUAGE.strings['Tracking']['ApplicationListen']).put(q_send)

        while True:
                
            received_data = q_recv.get()

            if 'Reload' in received_data:
                try:
                    running_apps.reload_file()
                except (NameError, UnboundLocalError):
                    running_apps = RunningApplications(queue=q_send)
                
                NOTIFY(LANGUAGE.strings['Tracking']['ApplistReload'], FILE_NAME=running_apps.applist.name)

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
                                NOTIFY(LANGUAGE.strings['Tracking']['ResolutionAppResize'],
                                       XRES_OLD=last_resolution[0], YRES_OLD=last_resolution[1],
                                       XRES=app_resolution[1][0], YRES=app_resolution[1][1])
                            elif app_resolution[0] != last_coordinates:
                                NOTIFY(LANGUAGE.strings['Tracking']['ResolutionAppMove'],
                                       XPOS_OLD=last_coordinates[0], YPOS_OLD=last_coordinates[1],
                                       XPOS=app_resolution[0][0], YPOS=app_resolution[0][1])
                        else:
                            NOTIFY(LANGUAGE.strings['Tracking']['ResolutionAppLoad'], 
                                   XRES=app_resolution[1][0], YRES=app_resolution[1][1])
                            
                        last_coordinates, last_resolution = app_resolution
                
                #Detect running program
                if current_app != previous_app:
                    
                    if running_apps.focus is None:
                        send['ApplicationResolution'] = None
                        app_start = LANGUAGE.strings['Tracking']['ApplicationStart']
                        app_end = LANGUAGE.strings['Tracking']['ApplicationEnd']
                    else:
                        # Somewhat hacky way to detect if the application is full screen spanning multiple monitors
                        # If this is the case, we want to record both monitors as normal
                        app_is_windowed = True
                        if MULTI_MONITOR and app_resolution is not None:
                            x_min = x_max = y_min = y_max = 0
                            for info in monitor_info():
                                x1, y1, x2, y2 = info
                                x_min = min(x_min, x1)
                                x_max = max(x_max, x2)
                                y_min = min(y_min, y1)
                                y_max = max(y_max, y2)
                            if (x_max - x_min, y_max - y_min) == app_resolution[1]:
                                app_is_windowed = False

                        send['ApplicationResolution'] = app_resolution if app_is_windowed else None
                        app_start = LANGUAGE.strings['Tracking']['ApplicationFocused']
                        app_end = LANGUAGE.strings['Tracking']['ApplicationUnfocused']
                
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


def _save_wrapper(q_send, program_name, data):
    """Handle saving the data files from the thread."""
    
    if program_name is not None and program_name[0] == TRACKING_DISABLE:
        return
    
    NOTIFY(LANGUAGE.strings['Tracking']['SavePrepare']).put(q_send)
    saved = False

    #Get how many attempts to use
    max_attempts = CONFIG['Save']['MaximumAttempts']
    
    compressed_data = prepare_file(data)
    
    #Attempt to save
    NOTIFY(LANGUAGE.strings['Tracking']['SaveStart']).put(q_send)
    for i in range(max_attempts):
        if save_data(program_name, compressed_data, _compress=False):
            NOTIFY(LANGUAGE.strings['Tracking']['SaveComplete']).put(q_send)
            saved = True
            break
        
        else:
            if max_attempts == 1:
                NOTIFY(LANGUAGE.strings['Tracking']['SaveIncompleteNoRetry']).put(q_send)
                return

            seconds = round_int(CONFIG['Save']['WaitAfterFail'])
            minutes = round_int(CONFIG['Save']['WaitAfterFail'] / 60)
            NOTIFY(LANGUAGE.strings['Tracking']['SaveIncompleteRetry'], ATTEMPT_CURRENT=i+1, ATTEMPT_MAX=max_attempts,
                   SECONDS=seconds, SECONDS_PLURAL=LANGUAGE.strings['Words'][('TimeSecondSingle', 'TimeSecondPlural')[seconds != 1]],
                   MINUTES=minutes, MINUTES_PLURAL=LANGUAGE.strings['Words'][('TimeMinuteSingle', 'TimeMinutePlural')[minutes != 1]]).put(q_send)

            time.sleep(CONFIG['Save']['WaitAfterFail'])
            
    if not saved:
        NOTIFY(LANGUAGE.strings['Tracking']['SaveIncompleteRetryFail']).put(q_send)


def _notify_queue_size(queue_main, queue_send=None):
    """Add number of queued commands to Notify class."""
    try:
        remaining_commands = queue_main.qsize()
    except NotImplementedError:
        return
    NOTIFY(LANGUAGE.strings['Tracking']['ScriptQueueSize'], NUMBER=remaining_commands, 
            COMMANDS_PLURAL=LANGUAGE.strings['Words'][('CommandSingle', 'CommandPlural')[remaining_commands != 1]]).put(queue_send)


def background_process(q_recv, q_send):
    """Function to handle all the data from the main thread."""
    try:
        NOTIFY(LANGUAGE.strings['Tracking']['ScriptThreadStart']).put(q_send)
        set_priority('low')
        
        store = {'Data': {None: LoadData()},
                 'Applications': {
                     DEFAULT_NAME: {
                        'Data': LoadData(),
                        'ActivitySinceLastSave': False,
                        'SavesSinceLastActivity': 0,
                     },
                 },
                 'CurrentProgram': None,
                 'CurrentProgramName': DEFAULT_NAME,
                 'Resolution': None,
                 'MonitorLimits': None,
                 'Offset': (0, 0),
                 'LastResolution': None,
                 'ActivitySinceLastSave': False,
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
        
        NOTIFY(LANGUAGE.strings['Tracking']['ProfileLoad'])
        _notify_queue_size(q_recv)
        NOTIFY.put(q_send)
        
        while True:
            received_data = q_recv.get()
            data = store['Applications'][store['CurrentProgramName']]['Data']
            
            #Increment the amount of time the script has been running for
            if 'Ticks' in received_data:
                data['Ticks']['Total'] += received_data['Ticks']['Total']
                data['Sessions'][-1][1] += received_data['Ticks']['Total']
                
                #Increment idle time if it reaches a threshold (>10 seconds)
                if store['LastIdle'] > received_data['Ticks']['Idle'] and store['LastIdle'] > CONFIG['Advanced']['IdleTime']:
                    data['Sessions'][-1][2] += store['LastIdle'] + CONFIG['Advanced']['IdleTime']
                store['LastIdle'] = received_data['Ticks']['Idle']
            
            #Save the data
            if 'Save' in received_data:
                remove_applications = []
                for application_name, application_data in store['Applications'].items():

                    #Data has been modified
                    if application_data['ActivitySinceLastSave']:
                        _save_wrapper(q_send, application_name, application_data['Data'])
                        application_data['ActivitySinceLastSave'] = False
                        application_data['SavesSinceLastActivity'] = 0
                        _notify_queue_size(q_recv)

                    #Data hasn't been modified
                    else:
                        application_data['SavesSinceLastActivity'] += 1
                        
                        #Mark the data for deletion to free up memory
                        NOTIFY('{}: {}'.format(application_name, application_data['SavesSinceLastActivity']), 2)
                        if application_data['SavesSinceLastActivity'] > CONFIG['Save']['SavesBeforeUnload']:
                            if application_name != store['CurrentProgramName']:
                                remove_applications.append(application_name)

                        #Detect why the save was skipped
                        try:
                            queue_size = q_recv.qsize()
                        except NotImplementedError:
                            queue_size = 0
                        
                        #Only show inactivity on the current program
                        #There shouldn't be any case where the current program is inactive and any others aren't
                        if application_name == store['CurrentProgramName']:
                            #Two different save commands probably next to each other
                            if queue_size > 2:
                                NOTIFY(LANGUAGE.strings['Tracking']['SaveSkipNoChange'], APPLICATION_NAME=application_name)
                            
                            #No activity since previous save
                            else:
                                time_since_save = CONFIG['Save']['Frequency'] * application_data['SavesSinceLastActivity']
                                seconds = int(time_since_save)
                                minutes = round(time_since_save / 60, 2)
                                if not minutes % 1:
                                    minutes = int(minutes)
                                hours = round(time_since_save / 3600, 2)
                                if not hours % 1:
                                    hours = int(hours)
                                seconds_plural = LANGUAGE.strings['Words'][('TimeSecondSingle', 'TimeSecondPlural')[seconds != 1]]
                                minutes_plural = LANGUAGE.strings['Words'][('TimeMinuteSingle', 'TimeMinutePlural')[minutes != 1]]
                                hours_plural = LANGUAGE.strings['Words'][('TimeHourSingle', 'TimeHourPlural')[hours != 1]]
                                NOTIFY(LANGUAGE.strings['Tracking']['SaveSkipInactivity'], 
                                    SECONDS=seconds, SECONDS_PLURAL=seconds_plural,
                                    MINUTES=minutes, MINUTES_PLURAL=minutes_plural,
                                    HOURS=hours, HOURS_PLURAL=hours_plural,
                                    APPLICATION_NAME=application_name
                                )
                q_send.put({'SaveFinished': None})

                NOTIFY(str(remove_applications), 2)
                for application_name in remove_applications:
                    del store['Applications'][application_name]
                    NOTIFY(LANGUAGE.strings['Tracking']['ApplicationUnload'], APPLICATION_NAME=application_name)

            update_resolution = False
            
            #Check for new program loaded
            if 'Program' in received_data:
                process_id, current_program = received_data['Program']
                
                if current_program != store['CurrentProgram']:
                    update_resolution = True
                    
                    store['CurrentProgramName'] = current_program[0] if current_program is not None else DEFAULT_NAME
                    NOTIFY(LANGUAGE.strings['Tracking']['ApplicationLoad'], APPLICATION_NAME=store['CurrentProgramName']).put(q_send)

                    # Load from cache
                    if store['CurrentProgramName'] in store['Applications']:
                        store['CurrentProgram'] = current_program
                        data = store['Applications'][store['CurrentProgramName']]['Data']

                    # Load from file
                    else:
                        #Load new profile
                        allow_new_session = current_program is not None or current_program is None and store['CurrentProgram'] is None
                        try:
                            if process_id is not None and process_id in store['ProcessIDs'][current_program]:
                                allow_new_session = False
                        except KeyError:
                            pass
                        if process_id is not None:
                            store['ProcessIDs'][current_program].add(process_id)
                        data = LoadData(current_program, _reset_sessions=allow_new_session)
                        store['CurrentProgram'] = current_program
                        store['Applications'][store['CurrentProgramName']] = {
                            'Data': data,
                            'ActivitySinceLastSave': False,
                            'SavesSinceLastActivity': 0,
                        }
                        
                        #Check new resolution
                        try:
                            store['ApplicationResolution'] = received_data['ApplicationResolution']
                        except KeyError:
                            pass
                        if store['ApplicationResolution'] is None:
                            check_resolution(data, store['Resolution'])
                        else:
                            check_resolution(data, store['ApplicationResolution'][1])
                            
                        if data['Ticks']['Total']:
                            NOTIFY(LANGUAGE.strings['Tracking']['ProfileLoad'])
                        else:
                            NOTIFY(LANGUAGE.strings['Tracking']['ProfileNew'])

                    _notify_queue_size(q_recv)
                NOTIFY.put(q_send)
            
            if 'ApplicationResolution' in received_data:
                store['ApplicationResolution'] = received_data['ApplicationResolution']
                if store['ApplicationResolution'] is not None:
                    check_resolution(data, store['ApplicationResolution'][1])
                    update_resolution = True

            if 'Resolution' in received_data:
                store['Resolution'] = received_data['Resolution']
                check_resolution(data, received_data['Resolution'])
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
                    if data['HistoryAnimation']['Tracks'][-1][0] != history_resolution:
                        raise IndexError
                except IndexError:
                    data['HistoryAnimation']['Tracks'].append([history_resolution])
            
            #Record key presses
            if 'KeyPress' in received_data:
                store['Applications'][store['CurrentProgramName']]['ActivitySinceLastSave'] = True
                record_key_press(store, received_data['KeyPress'])
            
            #Record time keys are held down
            if 'KeyHeld' in received_data:
                record_key_held(store, received_data['KeyHeld'])
                store['Applications'][store['CurrentProgramName']]['ActivitySinceLastSave'] = True
            
            #Record button presses
            if 'GamepadButtonPress' in received_data:
                store['Applications'][store['CurrentProgramName']]['ActivitySinceLastSave'] = True
                record_gamepad_pressed(store, received_data['GamepadButtonPress'])
            
            #Record how long buttons are held
            if 'GamepadButtonHeld' in received_data:
                store['Applications'][store['CurrentProgramName']]['ActivitySinceLastSave'] = True
                record_gamepad_held(store, received_data['GamepadButtonHeld'])
                        
            #Axis updates
            if 'GamepadAxis' in received_data:
                store['Applications'][store['CurrentProgramName']]['ActivitySinceLastSave'] = True
                record_gamepad_axis(store, received_data['GamepadAxis'])
            
            #Calculate and track mouse movement
            if 'MouseMove' in received_data:
                store['Applications'][store['CurrentProgramName']]['ActivitySinceLastSave'] = True
                record_mouse_move(store, received_data['MouseMove'])
                
                #Add to history if set
                if CONFIG['Main']['HistoryLength']:
                    data['HistoryAnimation']['Tracks'][-1].append(received_data['MouseMove'][1])
                
                #Compress tracks if the count gets too high
                max_track_value = CONFIG['Advanced']['CompressTrackMax']
                if not max_track_value:
                    max_track_value = MAX_INT
                
                if data['Ticks']['Tracks'] > max_track_value:
                    NOTIFY(LANGUAGE.strings['Tracking']['CompressStart'], TRACK_TYPE='tracks').put(q_send)
                    
                    compress_tracks(store, CONFIG['Advanced']['CompressTrackAmount'])
                    
                    NOTIFY(LANGUAGE.strings['Tracking']['CompressEnd'], TRACK_TYPE='tracks')
                    _notify_queue_size(q_recv)
                
            #Record mouse clicks
            if 'MouseClick' in received_data:
                store['Applications'][store['CurrentProgramName']]['ActivitySinceLastSave'] = True
                record_click_single(store, received_data['MouseClick'])
                    
            #Record double clicks
            if 'DoubleClick' in received_data:
                store['Applications'][store['CurrentProgramName']]['ActivitySinceLastSave'] = True
                record_click_double(store, received_data['DoubleClick'])
            
            #Trim the history list if too long
            if 'HistoryCheck' in received_data:
                max_length = CONFIG['Main']['HistoryLength'] * UPDATES_PER_SECOND
                history_trim(store, max_length)
                        
            data['Ticks']['Recorded'] += 1
            
            if 'Quit' in received_data or 'Exit' in received_data:
                return

            NOTIFY.put(q_send)
        
        #Exit process (this shouldn't happen for now)
        NOTIFY(LANGUAGE.strings['Tracking']['ScriptThreadEnd']).put(q_send)
        _save_wrapper(q_send, store['CurrentProgramName'], data)
            
    except Exception:
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
        
        check_resolution(store['Applications'][store['CurrentProgramName']]['Data'], resolution)
        return ((x - x_offset, y - y_offset), resolution)
        
    else:
        resolution = store['Resolution']
        
        return ((x, y), resolution)
        

def history_trim(store, desired_length):
    """Trim the history animation to the desired length."""
    
    history = store['Applications'][store['CurrentProgramName']]['Data']['HistoryAnimation']['Tracks']
    
    #Delete all history
    if not desired_length:
        store['Applications'][store['CurrentProgramName']]['Data']['HistoryAnimation']['Tracks'] = [history[-1][0]]
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
            
            store['Applications'][store['CurrentProgramName']]['Data']['HistoryAnimation']['Tracks'] = history
            return True
            
    return False


def _record_click(store, received_data, click_type):
    for mouse_button_index, (x, y) in received_data:
        
        try:
            (x, y), resolution = get_monitor_coordinate(x, y, store)
        except TypeError:
            continue
        
        mouse_button = ['Left', 'Middle', 'Right'][mouse_button_index]
        store['Applications'][store['CurrentProgramName']]['Data']['Resolution'][resolution]['Clicks'][click_type][mouse_button][y][x] += 1


def record_click_single(store, received_data):
    return _record_click(store, received_data, 'Single')


def record_click_double(store, received_data):
    return _record_click(store, received_data, 'Double')
    

def compress_tracks(store, multiplier):
    data = store['Applications'][store['CurrentProgramName']]['Data']
    for maps in data['Resolution'].values():
        maps['Tracks'] = numpy.divide(maps['Tracks'], multiplier, as_int=True)
        maps['StrokesSeparate']['Left'] = numpy.divide(maps['StrokesSeparate']['Left'], multiplier, as_int=True)
        maps['StrokesSeparate']['Middle'] = numpy.divide(maps['StrokesSeparate']['Middle'], multiplier, as_int=True)
        maps['StrokesSeparate']['Right'] = numpy.divide(maps['StrokesSeparate']['Right'], multiplier, as_int=True)
            
    data['Ticks']['Tracks'] //= multiplier
    data['Ticks']['Tracks'] = int(data['Ticks']['Tracks'])
    data['Ticks']['Session']['Tracks'] //= multiplier
    data['Ticks']['Session']['Tracks'] = int(data['Ticks']['Session']['Tracks'])
    
    
def _record_gamepad(store, received_data, press_type):
    data = store['Applications'][store['CurrentProgramName']]['Data']
    for button_id in received_data:
        try:
            data['Gamepad']['All']['Buttons'][press_type][button_id] += 1
        except KeyError:
            data['Gamepad']['All']['Buttons'][press_type][button_id] = 1
        try:
            data['Gamepad']['Session']['Buttons'][press_type][button_id] += 1
        except KeyError:
            data['Gamepad']['Session']['Buttons'][press_type][button_id] = 1


def record_gamepad_pressed(store, received_data):
    return _record_gamepad(store, received_data, 'Pressed')
    

def record_gamepad_held(store, received_data):
    return _record_gamepad(store, received_data, 'Held')


def record_gamepad_axis(store, received_data):
    data = store['Applications'][store['CurrentProgramName']]['Data']
    for controller_axis in received_data:
        for axis, amount in iteritems(controller_axis):
            try:
                data['Gamepad']['All']['Axis'][axis][amount] += 1
            except KeyError:
                try:
                    data['Gamepad']['All']['Axis'][axis][amount] = 1
                except KeyError:
                    data['Gamepad']['All']['Axis'][axis] = {amount: 1}
            try:
                data['Gamepad']['Session']['Axis'][axis][amount] += 1
            except KeyError:
                try:
                    data['Gamepad']['Session']['Axis'][axis][amount] = 1
                except KeyError:
                    data['Gamepad']['Session']['Axis'][axis] = {amount: 1}    


def _record_keypress(key_dict, *args):
    """Quick way of recording keypresses that doesn't involve a million try/excepts."""

    everything = key_dict['All']
    session = key_dict['Session']
    
    for i in args[:-1]:
        try:
            everything[i]
        except KeyError:
            everything[i] = {}
        everything = everything[i]
        try:
            session[i]
        except KeyError:
            session[i] = {}
        session = session[i]
    
    try:
        everything[args[-1]] += 1
    except KeyError:
        everything[args[-1]] = 1
    try:
        session[args[-1]] += 1
    except KeyError:
        session[args[-1]] = 1


def record_key_press(store, received_data):
    data = store['Applications'][store['CurrentProgramName']]['Data']

    for key in received_data:
        _record_keypress(data['Keys'], 'Pressed', key)
        
        if key not in KEY_STATS:
            store['KeyTrack']['LastKey'] = None
            
        else:
            #Record mistakes
            #Only records the key if a single backspace is used
            if key == 8:
                last = store['KeyTrack']['LastKey']
                if last is not None and last != 8:
                    store['KeyTrack']['Backspace'] = last
                else:
                    store['KeyTrack']['Backspace'] = False
            elif store['KeyTrack']['Backspace']:
                _record_keypress(data['Keys'], 'Mistakes', store['KeyTrack']['Backspace'], key)
                store['KeyTrack']['Backspace'] = False
            
            #Record interval between key presses
            if store['KeyTrack']['Time'] is not None and store['KeyTrack']['LastKey'] is not None:
                time_difference = data['Ticks']['Total'] - store['KeyTrack']['Time']
                if CONFIG['Advanced']['KeypressIntervalMax'] < 0 or time_difference <= CONFIG['Advanced']['KeypressIntervalMax']:
                    _record_keypress(data['Keys'], 'Intervals', 'Total', time_difference)
                    _record_keypress(data['Keys'], 'Intervals', 'Individual', store['KeyTrack']['LastKey'], key, time_difference)
            store['KeyTrack']['LastKey'] = key
            store['KeyTrack']['Time'] = data['Ticks']['Total']
        

def record_key_held(store, received_data):
    data = store['Applications'][store['CurrentProgramName']]['Data']
    for key in received_data:
        _record_keypress(data['Keys'], 'Held', key)
        
        
def record_mouse_move(store, received_data):
    data = store['Applications'][store['CurrentProgramName']]['Data']

    store['Applications'][store['CurrentProgramName']]['ActivitySinceLastSave'] = True
    resolution = 0
    _resolution = -1
    
    start, end, clicked = received_data
    distance = find_distance(end, start)
    
    #Misc stats
    data['Distance']['Tracks'] += distance
    continuous = store['LastTrackUpdate'] + 1 == data['Ticks']['Total']
    
    #Calculate the pixels in the line
    if start is None:
        mouse_coordinates = [end]
    else:
        mouse_coordinates = [start] + calculate_line(start, end) + [end]
        
    #Make sure resolution exists in data
    if store['ApplicationResolution'] is not None:
        check_resolution(data, store['ApplicationResolution'][1])
        
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
            check_resolution(data, resolution)
            if resolution != _resolution:
                check_resolution(data, resolution)
            _resolutions = [resolution, _resolution]
    
    #Write each pixel to the dictionary
    for (x, y) in mouse_coordinates:
    
        try:
            (x, y), resolution = get_monitor_coordinate(x, y, store)
        except TypeError:
            continue
        
        try:
            data['Resolution'][resolution]['Tracks'][y][x] = data['Ticks']['Tracks']
            if continuous:
                old_value = data['Resolution'][resolution]['Speed'][y][x]
                data['Resolution'][resolution]['Speed'][y][x] = max(distance, old_value)
                if clicked:
                    old_value = data['Resolution'][resolution]['Strokes'][y][x]
                    data['Resolution'][resolution]['Strokes'][y][x] = max(distance, old_value)
                
                #Testing separate maps for strokes
                for mouse_button, click_type in enumerate(('Left', 'Middle', 'Right')):
                    if mouse_button in clicked:
                        data['Resolution'][resolution]['StrokesSeparate'][click_type][y][x] = data['Ticks']['Tracks']
                    else:
                        data['Resolution'][resolution]['StrokesSeparate'][click_type][y][x] = 0
        
        #The IndexError here is super rare and I can't replicate it,
        #so may as well just ignore
        except TypeError:
            pass
    
    store['LastTrackUpdate'] = data['Ticks']['Total']
    data['Ticks']['Tracks'] += 1