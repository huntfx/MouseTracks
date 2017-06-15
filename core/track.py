from __future__ import division
from sys import version_info
import time
import sys
import traceback

from core.constants import CONFIG
from core.files import load_program, save_program
from core.functions import calculate_line, RunningPrograms, find_distance, get_items
from core.messages import *
from core.os import MULTI_MONITOR, monitor_info

if version_info == 2:
    range = xrange
    

def running_processes(q_recv, q_send, background_send):
    """Check for running processes.
    As refreshing the list takes some time but not CPU, this is put in its own thread
    and sends the currently running program to the backgrund process.
    """
    running = RunningPrograms()
    previous = None
        
    while True:
            
        received_data = q_recv.get()

        if 'Reload' in received_data:
            running.reload_file()
            NOTIFY(PROGRAM_RELOAD)

        if 'Update' in received_data:
            running.refresh()
            current = running.check()
            if current != previous:
                if current is None:
                    NOTIFY(PROGRAM_QUIT)
                else:
                    NOTIFY(PROGRAM_STARTED, current)
                NOTIFY.send(q_send)
                background_send.put({'Program': current})
                previous = current


def _save_wrapper(q_send, program_name, data, new_program=False):
    
    NOTIFY(SAVE_START)
    NOTIFY.send(q_send)
    saved = False

    #Get how many attempts to use
    if new_program:
        max_attempts = CONFIG['Save']['MaximumAttemptsSwitch']
    else:
        max_attempts = CONFIG['Save']['MaximumAttemptsNormal']

    #Attempt to save
    for i in range(max_attempts):
        if save_program(program_name, data):
            NOTIFY(SAVE_SUCCESS)
            NOTIFY.send(q_send)
            saved = True
            break
        
        else:
            if max_attempts == 1:
                NOTIFY(SAVE_FAIL)
                return
            NOTIFY(SAVE_FAIL_RETRY, CONFIG['Save']['WaitAfterFail'],
                         i, max_attempts)
            NOTIFY.send(q_send)
            time.sleep(CONFIG['Save']['WaitAfterFail'])
            
    if not saved:
        NOTIFY(SAVE_FAIL_END)


def monitor_offset(coordinate, monitor_limits):
    if coordinate is None:
        return
    mx, my = coordinate
    for x1, y1, x2, y2 in monitor_limits:
        if x1 <= mx < x2 and y1 <= my < y2:
            return ((x2 - x1, y2 - y1), (x1, y1))
            
            
def _check_resolution(store, resolution):
    if resolution is None:
        return
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
                 'LastResolution': None}
        
        NOTIFY(DATA_LOADED)
        NOTIFY(QUEUE_SIZE, q_recv.qsize())
        NOTIFY.send(q_send)

        maps = store['Data']['Maps']
        tick_count = store['Data']['Ticks']['Current']
        
        
        while True:
            
            received_data = q_recv.get()
            check_resolution = False
            
            if 'Save' in received_data:
                _save_wrapper(q_send, store['LastProgram'], store['Data'], False)
                NOTIFY(QUEUE_SIZE, q_recv.qsize())

            if 'Program' in received_data:
                current_program = received_data['Program']
                
                if current_program != store['LastProgram']:

                    _check_resolution(store, store['Resolution'])
                    store['ResolutionList'] = set()
                    if current_program is None:
                        NOTIFY(PROGRAM_LOADING)
                    else:
                        NOTIFY(PROGRAM_LOADING, current_program)
                    NOTIFY.send(q_send)
                        
                    _save_wrapper(q_send, store['LastProgram'], store['Data'], True)
                        
                    store['LastProgram'] = current_program
                    store['Data'] = load_program(current_program)
                    maps = store['Data']['Maps']
                    tick_count = store['Data']['Ticks']['Current']
                        
                    if store['Data']['Ticks']['Total']:
                        NOTIFY(DATA_LOADED)
                    else:
                        NOTIFY(DATA_NOTFOUND)
                            
                    NOTIFY(QUEUE_SIZE, q_recv.qsize())
                NOTIFY.send(q_send)

            if 'Resolution' in received_data:
                store['Resolution'] = received_data['Resolution']
                _check_resolution(store, store['Resolution'])
            
            if 'MonitorLimits' in received_data:
                store['ResolutionTemp'] = received_data['MonitorLimits']
            
            #Record key presses
            if 'KeyPress' in received_data:
                for key in received_data['KeyPress']:
                    try:
                        store['Data']['Keys']['Pressed'][key] += 1
                    except KeyError:
                        store['Data']['Keys']['Pressed'][key] = 1
            
            #Record time keys are held down
            if 'KeyHeld' in received_data:
                for key in received_data['KeyHeld']:
                    try:
                        store['Data']['Keys']['Held'][key] += 1
                    except KeyError:
                        store['Data']['Keys']['Held'][key] = 1
            
            #Calculate and track mouse movement
            if 'MouseMove' in received_data:
                start, end = received_data['MouseMove']
                #distance = find_distance(end, start)
                
                #Calculate the pixels in the line
                if end is None:
                    raise TypeError('debug - mouse moved without coordinates')
                if start is None:
                    mouse_coordinates = [end]
                else:
                    mouse_coordinates = [start, end] + calculate_line(start, end)

                #Write each pixel to the dictionary
                for pixel in mouse_coordinates:
                    if MULTI_MONITOR:
                    
                        try:
                            resolution, offset = monitor_offset(pixel, store['ResolutionTemp'])
                        except TypeError:
                            store['ResolutionTemp'] = monitor_info()
                            try:
                                resolution, offset = monitor_offset(pixel, store['ResolutionTemp'])
                            except TypeError:
                                raise TypeError('couldn\'t determine where {} was. monitor boundaries: {}'
                                                '. please send me the above message'.format(pixel, store['ResolutionTemp']))
                        
                        pixel = (pixel[0] - offset[0], pixel[1] - offset[1])
                        if resolution not in store['ResolutionList']:
                            _check_resolution(store, resolution)
                            store['ResolutionList'].add(resolution)
                            
                    else:
                        resolution = store['Resolution']
                        
                    maps['Tracks'][resolution][pixel] = tick_count['Tracks']
                
                tick_count['Tracks'] += 1
                
                #Compress tracks if the count gets too high
                if tick_count['Tracks'] > CONFIG['CompressMaps']['TrackMaximum']:
                    compress_multplier = CONFIG['CompressMaps']['TrackReduction']
                    NOTIFY(MOUSE_COMPRESS_START, 'track')
                    NOTIFY.send(q_send)
                    
                    tracks = maps['Tracks']
                    for resolution in tracks.keys():
                        tracks[resolution] = {k: int(v // compress_multplier)
                                              for k, v in get_items(tracks[resolution])}
                        tracks[resolution] = {k: v for k, v in get_items(tracks[resolution]) if v}
                        if not tracks[resolution]:
                            del tracks[resolution]
                    NOTIFY(MOUSE_COMPRESS_END, 'track')
                    NOTIFY(QUEUE_SIZE, q_recv.qsize())
                    tick_count['Tracks'] //= compress_multplier

            #Record mouse clicks
            if 'MouseClick' in received_data:
                for mouse_button, pixel in received_data['MouseClick']:
                    if MULTI_MONITOR:
                    
                        try:
                            resolution, offset = monitor_offset(pixel, store['ResolutionTemp'])
                        except TypeError:
                            store['ResolutionTemp'] = monitor_info()
                            try:
                                resolution, offset = monitor_offset(pixel, store['ResolutionTemp'])
                            except TypeError:
                                raise TypeError('couldn\'t determine where {} was. monitor boundaries: {}'
                                                '. please send me the above message'.format(pixel, store['ResolutionTemp']))
                            
                        pixel = (pixel[0] - offset[0], pixel[1] - offset[1])
                        
                    else:
                        resolution = store['Resolution']
                        
                    try:
                        maps['Clicks'][resolution][mouse_button][pixel] += 1
                    except KeyError:
                        maps['Clicks'][resolution][mouse_button][pixel] = 1
                
            #Increment the amount of time the script has been running for
            if 'Ticks' in received_data:
                store['Data']['Ticks']['Total'] += received_data['Ticks']
            store['Data']['Ticks']['Recorded'] += 1

            NOTIFY.send(q_send)
            
            
    except Exception as e:
        q_send.put(traceback.format_exc())
        return
