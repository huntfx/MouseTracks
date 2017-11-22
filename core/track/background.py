#todo: check no crash when resolution doesnt update after plugging in monitor
from __future__ import division, absolute_import
import time
import traceback

from core.applications import RunningApplications
from core.compatibility import range, get_items
from core.config import CONFIG
from core.constants import MAX_INT, DISABLE_TRACKING, IGNORE_TRACKING
from core.files import LoadData, save_data, prepare_file
from core.maths import calculate_line, find_distance
from core.notify import *
from core.os import MULTI_MONITOR, monitor_info
import core.numpy as numpy
    

def running_processes(q_recv, q_send, background_send):
    """Check for running processes.
    As refreshing the list takes some time but not CPU, this is put in its own thread
    and sends the currently running program to the backgrund process.
    """
    try:
        previous_app = None
        last_coordinates = None
        last_resolution = None
            
        while True:
                
            received_data = q_recv.get()

            if 'Reload' in received_data:
                try:
                    running_apps.reload_file()
                except NameError:
                    running_apps = RunningApplications(queue=q_send)
                NOTIFY(APPLICATION_RELOAD)

            if 'Update' in received_data:
                running_apps.refresh()
                
                current_app = running_apps.check()
                send = {}
                
                if current_app is not None and current_app[0] == IGNORE_TRACKING:
                    current_app = None
                
                #Send custom resolution
                if running_apps.focus is not None:
                    #NOTIFY_DEBUG(running_apps.focused_exe, running_apps.focused_name)
                    
                    if current_app is None:
                        cust_res = None
                    
                    else:
                        cust_res = [running_apps.focus.rect(), running_apps.focus.resolution()]
                        
                        if current_app == previous_app:
                            if cust_res[1] != last_resolution:
                                NOTIFY(APPLICATION_RESIZE, last_resolution, cust_res[1])
                            elif cust_res[0] != last_coordinates:
                                NOTIFY(APPLICATION_MOVE, last_coordinates, cust_res[0])
                        else:
                            NOTIFY(APPLICATION_RESOLUTION, cust_res[1])
                            
                        last_coordinates, last_resolution = cust_res
                            
                    send['ApplicationResolution'] = cust_res
                
                #Detect running program
                if current_app != previous_app:
                    
                    if running_apps.focus is None:
                        start = APPLICATION_STARTED
                        end = APPLICATION_QUIT
                        send['ApplicationResolution'] = None
                    else:
                        start = APPLICATION_FOCUSED
                        end = APPLICATION_UNFOCUSED
                
                    if current_app is None:
                        NOTIFY(end, previous_app)
                    else:
                        if running_apps.focus is not None and previous_app is not None:
                            NOTIFY(APPLICATION_UNFOCUSED, previous_app)
                        NOTIFY(start, current_app)
                        
                    NOTIFY.send(q_send)
                    send['Program'] = current_app
                    
                    previous_app = current_app
                
                if send:
                    background_send.put(send)
    
    #Catch error after KeyboardInterrupt
    except EOFError:
        return

def _save_wrapper(q_send, program_name, data, new_program=False):
    """Handle saving the data files from the thread."""
    
    if program_name is not None and program_name[0] == DISABLE_TRACKING:
        return
    
    NOTIFY(SAVE_PREPARE)
    NOTIFY.send(q_send)
    saved = False

    #Get how many attempts to use
    if new_program:
        max_attempts = CONFIG['Save']['MaximumAttemptsSwitch']
    else:
        max_attempts = CONFIG['Save']['MaximumAttemptsNormal']
    
    compressed_data = prepare_file(data)
    
    #Attempt to save
    NOTIFY(SAVE_START)
    NOTIFY.send(q_send)
    for i in range(max_attempts):
        if save_data(program_name, compressed_data, _compress=False):
            NOTIFY(SAVE_SUCCESS)
            NOTIFY.send(q_send)
            saved = True
            break
        
        else:
            if max_attempts == 1:
                NOTIFY(SAVE_FAIL)
                return
            NOTIFY(SAVE_FAIL_RETRY, CONFIG['Save']['WaitAfterFail'], i, max_attempts)
            NOTIFY.send(q_send)
            time.sleep(CONFIG['Save']['WaitAfterFail'])
            
    if not saved:
        NOTIFY(SAVE_FAIL_END)


def monitor_offset(coordinate, monitor_limits):
    """Detect which monitor the mouse is currently over."""
    if coordinate is None:
        return
    mx, my = coordinate
    for x1, y1, x2, y2 in monitor_limits:
        if x1 <= mx < x2 and y1 <= my < y2:
            return ((x2 - x1, y2 - y1), (x1, y1))
            
            
def check_resolution(data, resolution):
    """Make sure resolution exists in data."""
    if resolution is None:
        return
    if not isinstance(resolution, tuple):
        raise ValueError('incorrect resolution: {}'.format(resolution))
        
    if resolution not in data['Resolution']:
        data['Resolution'][resolution] = {'Tracks': numpy.array(resolution, create=True), 'Clicks': {}}
        clicks = data['Resolution'][resolution]['Clicks']
        clicks['All'] = {'Single': {'Left': numpy.array(resolution, create=True),
                                    'Middle': numpy.array(resolution, create=True),
                                    'Right': numpy.array(resolution, create=True)},
                         'Double': {'Left': numpy.array(resolution, create=True),
                                    'Middle': numpy.array(resolution, create=True),
                                    'Right': numpy.array(resolution, create=True)}}
        clicks['Session'] = {'Single': {'Left': numpy.array(resolution, create=True),
                                        'Middle': numpy.array(resolution, create=True),
                                        'Right': numpy.array(resolution, create=True)},
                             'Double': {'Left': numpy.array(resolution, create=True),
                                        'Middle': numpy.array(resolution, create=True),
                                        'Right': numpy.array(resolution, create=True)}}

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
            
            
def background_process(q_recv, q_send):
    """Function to handle all the data from the main thread."""
    try:
        NOTIFY(START_THREAD)
        NOTIFY.send(q_send)
        
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
                 'FirstLoad': True
                }
        
        NOTIFY(DATA_LOADED)
        try:
            NOTIFY(QUEUE_SIZE, q_recv.qsize())
        except NotImplementedError:
            pass
        NOTIFY.send(q_send)
        
        while True:
            received_data = q_recv.get()
            
            #Increment the amount of time the script has been running for
            if 'Ticks' in received_data:
                store['Data']['Ticks']['Total'] += received_data['Ticks']
            
            #Save the data
            if 'Save' in received_data:
                if store['ActivitySinceLastSave']:
                    _save_wrapper(q_send, store['LastProgram'], store['Data'], False)
                    store['ActivitySinceLastSave'] = False
                    store['SavesSkipped'] = 0
                    
                    try:
                        NOTIFY(QUEUE_SIZE, q_recv.qsize())
                    except NotImplementedError:
                        pass
                else:
                    store['SavesSkipped'] += 1
                    
                    try:
                        NOTIFY(SAVE_SKIP, CONFIG['Save']['Frequency'] * store['SavesSkipped'], q_recv.qsize())
                    except NotImplementedError:
                        pass
                q_send.put({'SaveFinished': None})
            
            #Check for new program loaded
            if 'Program' in received_data:
                current_program = received_data['Program']
                
                if current_program != store['LastProgram']:
                    
                    if current_program is None:
                        NOTIFY(APPLICATION_LOADING)
                    else:
                        NOTIFY(APPLICATION_LOADING, current_program)
                    NOTIFY.send(q_send)
                    
                    #Save old profile
                    _save_wrapper(q_send, store['LastProgram'], store['Data'], True)
                    
                    #Load new profile
                    store['LastProgram'] = current_program
                    store['Data'] = LoadData(current_program)
                    store['ActivitySinceLastSave'] = False
                    
                    #Check new resolution
                    try:
                        store['ApplicationResolution'] = received_data['ApplicationResolution']
                    except AttributeError:
                        pass
                    if store['ApplicationResolution'] is None:
                        check_resolution(store['Data'], store['Resolution'])
                    else:
                        check_resolution(store['Data'], store['ApplicationResolution'][1])
                        
                    if store['Data']['Ticks']['Total']:
                        NOTIFY(DATA_LOADED)
                    else:
                        NOTIFY(DATA_NOTFOUND)
                    
                    try:
                        NOTIFY(QUEUE_SIZE, q_recv.qsize())
                    except NotImplementedError:
                        pass
                NOTIFY.send(q_send)
            
            if 'ApplicationResolution' in received_data:
                store['ApplicationResolution'] = received_data['ApplicationResolution']
                if store['ApplicationResolution'] is not None:
                    check_resolution(store['Data'], store['ApplicationResolution'][1])

            if 'Resolution' in received_data:
                store['Resolution'] = received_data['Resolution']
                check_resolution(store['Data'], received_data['Resolution'])
                
                if store['LastResolution'] != store['Resolution']:
                    store['Data']['HistoryAnimation']['Tracks'].append([store['Resolution']])
                    store['LastResolution'] = store['Resolution']
            
            if 'MonitorLimits' in received_data:
                store['MonitorLimits'] = received_data['MonitorLimits']
                
                if store['LastResolution'] != store['MonitorLimits']:
                    store['Data']['HistoryAnimation']['Tracks'].append([store['MonitorLimits']])
                    store['LastResolution'] = store['MonitorLimits']
            
            #Record key presses
            if 'KeyPress' in received_data:
                store['ActivitySinceLastSave'] = True
                
                for key in received_data['KeyPress']:
                
                    _record_keypress(store['Data']['Keys'], 'Pressed', key)
                    
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
                    if store['KeyTrack']['Time'] is not None:
                        time_difference = store['Data']['Ticks']['Total'] - store['KeyTrack']['Time']
                        _record_keypress(store['Data']['Keys'], 'Intervals', 'Total', time_difference)
                        _record_keypress(store['Data']['Keys'], 'Intervals', 'Individual', store['KeyTrack']['LastKey'], key, time_difference)
                    
                    store['KeyTrack']['LastKey'] = key
                    store['KeyTrack']['Time'] = store['Data']['Ticks']['Total']
            
            #Record time keys are held down
            if 'KeyHeld' in received_data:
                store['ActivitySinceLastSave'] = True
                
                for key in received_data['KeyHeld']:
                    _record_keypress(store['Data']['Keys'], 'Held', key)
            
            #Record button presses
            try:
                pressed_buttons = received_data['GamepadButtonPress']
            except KeyError:
                pass
            else:
                store['ActivitySinceLastSave'] = True
                for button_id in pressed_buttons:
                    try:
                        store['Data']['Gamepad']['All']['Buttons']['Pressed'][button_id] += 1
                    except KeyError:
                        store['Data']['Gamepad']['All']['Buttons']['Pressed'][button_id] = 1
                    try:
                        store['Data']['Gamepad']['Session']['Buttons']['Pressed'][button_id] += 1
                    except KeyError:
                        store['Data']['Gamepad']['Session']['Buttons']['Pressed'][button_id] = 1
            
            #Record how long buttons are held
            try:
               held_buttons = received_data['GamepadButtonHeld']
            except KeyError:
                pass
            else:
                store['ActivitySinceLastSave'] = True
                for button_id in held_buttons:
                    try:
                        store['Data']['Gamepad']['All']['Buttons']['Held'][button_id] += 1
                    except KeyError:
                        store['Data']['Gamepad']['All']['Buttons']['Held'][button_id] = 1
                    try:
                        store['Data']['Gamepad']['Session']['Buttons']['Held'][button_id] += 1
                    except KeyError:
                        store['Data']['Gamepad']['Session']['Buttons']['Held'][button_id] = 1
                        
            #Axis updates
            try:
                axis_updates = received_data['GamepadAxis']
            except KeyError:
                pass
            else:
                for controller_axis in axis_updates:
                    for axis, amount in get_items(controller_axis):
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
                                
            
            #Calculate and track mouse movement
            if 'MouseMove' in received_data:
                store['ActivitySinceLastSave'] = True
                resolution = 0
                _resolution = -1
                
                start, end = received_data['MouseMove']
                #distance = find_distance(end, start)
                
                store['Data']['HistoryAnimation']['Tracks'][-1].append(end)
                
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
                        
                store['Data']['Ticks']['Tracks'] += 1
                
                #Compress tracks if the count gets too high
                max_track_value = CONFIG['Advanced']['CompressTrackMax']
                if not max_track_value:
                    max_track_value = MAX_INT
                
                '''
                if store['Data']['Ticks']['Tracks'] > max_track_value:
                    compress_multplier = CONFIG['Advanced']['CompressTrackAmount']
                    NOTIFY(TRACK_COMPRESS_START, 'track')
                    NOTIFY.send(q_send)
                    
                    tracks = store['Data']['Maps']['Tracks']
                    for resolution in tracks.keys():
                        tracks[resolution] = numpy.divide(tracks[resolution], compress_multplier, as_int=True)
                        #if not numpy.count(tracks[resolution]):
                        #    del tracks[resolution]
                            
                    NOTIFY(TRACK_COMPRESS_END, 'track')
                    try:
                        NOTIFY(QUEUE_SIZE, q_recv.qsize())
                    except NotImplementedError:
                        pass
                        
                    store['Data']['Ticks']['Tracks'] //= compress_multplier
                    store['Data']['Ticks']['Session']['Tracks'] //= compress_multplier
                    store['Data']['Ticks']['Tracks'] = int(store['Data']['Ticks']['Tracks'])
                    store['Data']['Ticks']['Session']['Tracks'] = int(store['Data']['Ticks']['Session']['Tracks'])
                    '''
                
            #Record mouse clicks
            if 'MouseClick' in received_data:
                store['ActivitySinceLastSave'] = True
                
                for mouse_button_index, (x, y) in received_data['MouseClick']:
                    
                    try:
                        (x, y), resolution = get_monitor_coordinate(x, y, store)
                    except TypeError:
                        continue
                    
                    mouse_button = ['Left', 'Middle', 'Right'][mouse_button_index]
                    
                    store['Data']['Resolution'][resolution]['Clicks']['All']['Single'][mouse_button][y][x] += 1
                    store['Data']['Resolution'][resolution]['Clicks']['Session']['Single'][mouse_button][y][x] += 1
                    
            #Record double clicks
            if 'DoubleClick' in received_data:
                store['ActivitySinceLastSave'] = True
                
                for mouse_button_index, (x, y) in received_data['DoubleClick']:
                                            
                    try:
                        (x, y), resolution = get_monitor_coordinate(x, y, store)
                    except TypeError:
                        continue
                    
                    mouse_button = ['Left', 'Middle', 'Right'][mouse_button_index]
                    store['Data']['Resolution'][resolution]['Clicks']['All']['Double'][mouse_button][y][x] += 1
                    store['Data']['Resolution'][resolution]['Clicks']['Session']['Double'][mouse_button][y][x] += 1
            
            
            #Trim the history list if too long
            if 'HistoryCheck' in received_data:
                history_len = [len(i) - 1 for i in store['Data']['HistoryAnimation']['Tracks']]
                if sum(history_len) > CONFIG['Main']['HistoryLength']:
                    count = 0
                    for i, value in enumerate(store['Data']['HistoryAnimation']['Tracks']):
                    
                        count += history_len[i]
                        if count >= CONFIG['Main']['HistoryLength']:
                            data = data[i:]
                            if count > CONFIG['Main']['HistoryLength']:
                                offset = data_len[i] - CONFIG['Main']['HistoryLength']
                                data[0] = [data[0][0]] + data[0][offset+1:]
                            break

            store['Data']['Ticks']['Recorded'] += 1
            
            if 'Quit' in received_data or 'Exit' in received_data:
                break

            NOTIFY.send(q_send)
        
        #Exit process (this shouldn't happen for now)
        NOTIFY(THREAD_EXIT)
        NOTIFY.send(q_send)
        _save_wrapper(q_send, store['LastProgram'], store['Data'], False)
            
    except Exception as e:
        q_send.put(traceback.format_exc())
        
    except KeyboardInterrupt:
        pass
