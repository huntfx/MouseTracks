from __future__ import division, absolute_import
#from queue import Empty
import time
import traceback

from core.applications import RunningApplications
from core.compatibility import range, get_items
from core.config import CONFIG
from core.constants import MAX_INT
from core.files import load_program, save_program, prepare_file
from core.maths import calculate_line, find_distance
from core.notify import *
from core.os import MULTI_MONITOR, monitor_info
    

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
                
                #Send custom resolution
                if running_apps.focus is not None:
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
                            
                    background_send.put({'CustomResolution': cust_res})
                    
                if current_app != previous_app:
                    
                    if running_apps.focus is None:
                        start = APPLICATION_STARTED
                        end = APPLICATION_QUIT
                        background_send.put({'CustomResolution': None})
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
                    background_send.put({'Program': current_app})
                    
                    previous_app = current_app
    
    #Catch error after KeyboardInterrupt
    except EOFError:
        return

def _save_wrapper(q_send, program_name, data, new_program=False):
    
    NOTIFY(SAVE_PREPARE)
    NOTIFY.send(q_send)
    saved = False

    #Get how many attempts to use
    if new_program:
        max_attempts = CONFIG['Save']['MaximumAttemptsSwitch']
    else:
        max_attempts = CONFIG['Save']['MaximumAttemptsNormal']
    
    oompressed_data = prepare_file(data)
    
    #Attempt to save
    NOTIFY(SAVE_START)
    NOTIFY.send(q_send)
    for i in range(max_attempts):
        if save_program(program_name, oompressed_data, compress=False):
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
            
            
def _check_resolution(store, resolution):
    """Make sure resolution exists as a key for each map."""
    if resolution is None:
        return
    if not isinstance(resolution, tuple):
        raise ValueError('incorrect resolution: {}'.format(resolution))
    if resolution not in store['Data']['Maps']['Tracks']:
        store['Data']['Maps']['Tracks'][resolution] = {}
    if resolution not in store['Data']['Maps']['Clicks']:
        store['Data']['Maps']['Clicks'][resolution] = [{}, {}, {}]


def background_process(q_recv, q_send):
    """Function to handle all the data from the main thread."""
    try:
        NOTIFY(START_THREAD)
        NOTIFY.send(q_send)
        
        store = {'Data': load_program(),
                 'LastProgram': None,
                 'Resolution': None,
                 'ResolutionTemp': None,
                 'ResolutionList': set(),
                 'Offset': (0, 0),
                 'LastResolution': None,
                 'ActivitySinceLastSave': False,
                 'SavesSkipped': 0,
                 'PingTimeout': CONFIG['Timer']['_Ping'] + 1,
                 'CustomResolution': None}
        
        NOTIFY(DATA_LOADED)
        try:
            NOTIFY(QUEUE_SIZE, q_recv.qsize())
        except NotImplementedError:
            pass
        NOTIFY.send(q_send)
        
        while True:
            received_data = q_recv.get()
            '''
            #Quit if data is not received by the ping interval
            #Seems buggy so disabling for now
            try:
                received_data = q_recv.get(timeout=store['PingTimeout'])
            except Empty:
                break
                '''
            
            check_resolution = False
            
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
                    store['Data'] = load_program(current_program)
                    store['ActivitySinceLastSave'] = False
                    
                    #Check new resolution
                    if store['CustomResolution'] is None:
                        _check_resolution(store, store['Resolution'])
                    else:
                        _check_resolution(store, store['CustomResolution'][1])
                    store['ResolutionList'] = set()
                        
                    if store['Data']['Ticks']['Total']:
                        NOTIFY(DATA_LOADED)
                    else:
                        NOTIFY(DATA_NOTFOUND)
                    
                    try:
                        NOTIFY(QUEUE_SIZE, q_recv.qsize())
                    except NotImplementedError:
                        pass
                NOTIFY.send(q_send)
            
            if 'CustomResolution' in received_data:
                
                store['CustomResolution'] = received_data['CustomResolution']
                if store['CustomResolution'] is not None:
                    _check_resolution(store, store['CustomResolution'][1])

            if 'Resolution' in received_data:
                store['Resolution'] = received_data['Resolution']
                _check_resolution(store, store['Resolution'])
            
            if 'MonitorLimits' in received_data:
                store['ResolutionTemp'] = received_data['MonitorLimits']
            
            #Record key presses
            if 'KeyPress' in received_data:
                store['ActivitySinceLastSave'] = True
                
                for key in received_data['KeyPress']:
                    try:
                        store['Data']['Keys']['All']['Pressed'][key] += 1
                    except KeyError:
                        store['Data']['Keys']['All']['Pressed'][key] = 1
                    try:
                        store['Data']['Keys']['Session']['Pressed'][key] += 1
                    except KeyError:
                        store['Data']['Keys']['Session']['Pressed'][key] = 1
            
            #Record time keys are held down
            if 'KeyHeld' in received_data:
                store['ActivitySinceLastSave'] = True
                
                for key in received_data['KeyHeld']:
                    try:
                        store['Data']['Keys']['All']['Held'][key] += 1
                    except KeyError:
                        store['Data']['Keys']['All']['Held'][key] = 1
                    try:
                        store['Data']['Keys']['Session']['Held'][key] += 1
                    except KeyError:
                        store['Data']['Keys']['Session']['Held'][key] = 1
            
            
            #Calculate and track mouse movement
            if 'MouseMove' in received_data:
                store['ActivitySinceLastSave'] = True
                resolution = 0
                _resolution = -1
                
                start, end = received_data['MouseMove']
                #distance = find_distance(end, start)
                
                #Calculate the pixels in the line
                if end is None:
                    raise TypeError('debug - mouse moved without coordinates')
                if start is None:
                    mouse_coordinates = [end]
                else:
                    mouse_coordinates = [start] + calculate_line(start, end) + [end]
                    
                #Don't bother calculating offset for each pixel
                #if both start and end are on the same monitor
                try:
                    resolution, offset = monitor_offset(start, store['ResolutionTemp'])
                    _resolution = monitor_offset(end, store['ResolutionTemp'])[0]
                except TypeError:
                    pass
                        
                #Write each pixel to the dictionary
                for pixel in mouse_coordinates:
                
                    if store['CustomResolution'] is not None:
                        try:
                            resolution, offset = monitor_offset(pixel, [store['CustomResolution'][0]])
                        except TypeError:
                            continue
                            
                        pixel = (pixel[0] - offset[0], pixel[1] - offset[1])
                    
                    elif MULTI_MONITOR:
                        
                        #Check if offset needs to be recalculated
                        if resolution != _resolution:
                            try:
                                resolution, offset = monitor_offset(pixel, store['ResolutionTemp'])
                            except TypeError:
                                store['ResolutionTemp'] = monitor_info()
                                try:
                                    resolution, offset = monitor_offset(pixel, store['ResolutionTemp'])
                                except TypeError:
                                    continue
                        
                        pixel = (pixel[0] - offset[0], pixel[1] - offset[1])
                        if resolution not in store['ResolutionList']:
                            _check_resolution(store, resolution)
                            store['ResolutionList'].add(resolution)
                            
                    else:
                        resolution = store['Resolution']
                        
                    store['Data']['Maps']['Tracks'][resolution][pixel] = store['Data']['Ticks']['Current']['Tracks']

                store['Data']['Ticks']['Current']['Tracks'] += 1
                
                #Compress tracks if the count gets too high
                max_track_value = CONFIG['CompressMaps']['TrackMaximum']
                if not max_track_value:
                    max_track_value = MAX_INT
                if store['Data']['Ticks']['Current']['Tracks'] > CONFIG['CompressMaps']['TrackMaximum']:
                    compress_multplier = CONFIG['CompressMaps']['TrackReduction']
                    NOTIFY(TRACK_COMPRESS_START, 'track')
                    NOTIFY.send(q_send)
                    
                    tracks = store['Data']['Maps']['Tracks']
                    for resolution in tracks.keys():
                        tracks[resolution] = {k: int(v // compress_multplier)
                                              for k, v in get_items(tracks[resolution])}
                        tracks[resolution] = {k: v for k, v in get_items(tracks[resolution]) if v}
                        if not tracks[resolution]:
                            del tracks[resolution]
                            
                    NOTIFY(TRACK_COMPRESS_END, 'track')
                    try:
                        NOTIFY(QUEUE_SIZE, q_recv.qsize())
                    except NotImplementedError:
                        pass
                    store['Data']['Ticks']['Current']['Tracks'] //= compress_multplier
                    store['Data']['Ticks']['Session']['Current'] //= compress_multplier

            #Record mouse clicks
            if 'MouseClick' in received_data:
                store['ActivitySinceLastSave'] = True
                
                for mouse_button, pixel in received_data['MouseClick']:
                
                    if store['CustomResolution'] is not None:
                        try:
                            resolution, offset = monitor_offset(pixel,  [store['CustomResolution'][0]])
                        except TypeError:
                            continue
                            
                        pixel = (pixel[0] - offset[0], pixel[1] - offset[1])
                            
                    elif MULTI_MONITOR:
                    
                        try:
                            resolution, offset = monitor_offset(pixel, store['ResolutionTemp'])
                        except TypeError:
                            store['ResolutionTemp'] = monitor_info()
                            try:
                                resolution, offset = monitor_offset(pixel, store['ResolutionTemp'])
                            except TypeError:
                                continue
                        
                        _check_resolution(store, resolution)
                        pixel = (pixel[0] - offset[0], pixel[1] - offset[1])
                        
                    else:
                        resolution = store['Resolution']
                        
                    try:
                        store['Data']['Maps']['Clicks'][resolution][mouse_button][pixel] += 1
                    except KeyError:
                        store['Data']['Maps']['Clicks'][resolution][mouse_button][pixel] = 1
                
            #Increment the amount of time the script has been running for
            if 'Ticks' in received_data:
                store['Data']['Ticks']['Total'] += received_data['Ticks']
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
