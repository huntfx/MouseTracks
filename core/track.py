from __future__ import division
from functions import calculate_line, RunningPrograms, find_distance
from messages import *
from files import load_program, save_program
from constants import CONFIG
import time
import sys
import traceback


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
            notify.queue(PROGRAM_RELOAD)

        if 'Update' in received_data:
            running.refresh()
            current = running.check()
            if current != previous:
                if current is None:
                    notify.queue(PROGRAM_QUIT)
                else:
                    notify.queue(PROGRAM_STARTED, current)
                _notify_send(q_send, notify)
                background_send.put({'Program': current})
                previous = current


def _notify_send(q_send, notify):
    """Wrapper to the notify class to send non empty values."""
    output = notify.output()
    if output:
        q_send.put(output)


def _save_wrapper(q_send, program_name, data, new_program=False):
    
    notify.queue(SAVE_START)
    _notify_send(q_send, notify)
    saved = False

    #Get how many attempts to use
    if new_program:
        max_attempts = CONFIG.data['Save']['MaximumAttemptsSwitch']
    else:
        max_attempts = CONFIG.data['Save']['MaximumAttemptsNormal']

    #Attempt to save
    for i in xrange(max_attempts):
        if save_program(program_name, data):
            notify.queue(SAVE_SUCCESS)
            _notify_send(q_send, notify)
            saved = True
            break
        
        else:
            if max_attempts == 1:
                notify.queue(SAVE_FAIL)
                return
            notify.queue(SAVE_FAIL_RETRY, CONFIG.data['Save']['WaitAfterFail'],
                         i, max_attempts)
            _notify_send(q_send, notify)
            time.sleep(CONFIG.data['Save']['WaitAfterFail'])
            
    if not saved:
        notify.queue(SAVE_FAIL_END)

        
def background_process(q_recv, q_send):
    """Function to handle all the data from the main thread."""
    try:
        notify.queue(START_THREAD)
        _notify_send(q_send, notify)
        
        store = {'Data': load_program(),
                 'LastProgram': None,
                 'Resolution': None}
        
        notify.queue(DATA_LOADED)
        notify.queue(QUEUE_SIZE, q_recv.qsize())
        _notify_send(q_send, notify)
        
        while True:
            
            received_data = q_recv.get()
            check_resolution = False
            
            if 'Save' in received_data:
                _save_wrapper(q_send, store['LastProgram'], store['Data'], False)
                notify.queue(QUEUE_SIZE, q_recv.qsize())

            if 'Program' in received_data:
                current_program = received_data['Program']
                
                if current_program != store['LastProgram']:

                    check_resolution = True
                    if current_program is None:
                        notify.queue(PROGRAM_LOADING)
                    else:
                        notify.queue(PROGRAM_LOADING, current_program)
                    _notify_send(q_send, notify)
                        
                    _save_wrapper(q_send, store['LastProgram'], store['Data'], True)
                        
                    store['LastProgram'] = current_program
                    store['Data'] = load_program(current_program)
                        
                    if store['Data']['Ticks']['Total']:
                        notify.queue(DATA_LOADED)
                    else:
                        notify.queue(DATA_NOTFOUND)
                            
                    notify.queue(QUEUE_SIZE, q_recv.qsize())
                _notify_send(q_send, notify)

            if 'Resolution' in received_data:
                check_resolution = True
                store['Resolution'] = received_data['Resolution']

            #Make sure resolution exists as a key
            if check_resolution:
                if store['Resolution'] not in store['Data']['Tracks']:
                    store['Data']['Tracks'][store['Resolution']] = {}
                if store['Resolution'] not in store['Data']['Clicks']:
                    store['Data']['Clicks'][store['Resolution']] = [{}, {}, {}]
                if store['Resolution'] not in store['Data']['Speed']:
                    store['Data']['Speed'][store['Resolution']] = {}
                if store['Resolution'] not in store['Data']['Combined']:
                    store['Data']['Combined'][store['Resolution']] = {}
            
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

            #Record mouse clicks
            if 'MouseClick' in received_data:
                for mouse_button, mouse_click in received_data['MouseClick']:
                    try:
                        store['Data']['Clicks'][store['Resolution']][mouse_button][mouse_click] += 1
                    except KeyError:
                        store['Data']['Clicks'][store['Resolution']][mouse_button][mouse_click] = 1
            
            #Calculate and track mouse movement
            if 'MouseMove' in received_data:
                start, end = received_data['MouseMove']
                distance = find_distance(end, start)
                combined = distance * store['Data']['Ticks']['Current']
                
                #Calculate the pixels in the line
                if start is None:
                    mouse_coordinates = [end]
                else:
                    mouse_coordinates = [start, end] + calculate_line(start, end)

                #Write each pixel to the dictionary
                for pixel in mouse_coordinates:
                    store['Data']['Tracks'][store['Resolution']][pixel] = store['Data']['Ticks']['Current']
                    try:
                        if store['Data']['Speed'][store['Resolution']][pixel] < distance:
                            raise KeyError()
                    except KeyError:
                        store['Data']['Speed'][store['Resolution']][pixel] = distance
                    try:
                        if store['Data']['Combined'][store['Resolution']][pixel] < combined:
                            raise KeyError()
                    except KeyError:
                        store['Data']['Combined'][store['Resolution']][pixel] = combined
                        
                store['Data']['Ticks']['Current'] += 1
                
                #Compress tracks if the count gets too high
                if store['Data']['Ticks']['Current'] > CONFIG.data['CompressTracks']['MaximumValue']:
                    compress_multplier = CONFIG.data['CompressTracks']['Reduction']
                    
                    #Compress tracks
                    tracks = store['Data']['Tracks']
                    for resolution in tracks.keys():
                        tracks[resolution] = {k: int(v // compress_multplier)
                                              for k, v in tracks[resolution].iteritems()}
                        tracks[resolution] = {k: v for k, v in tracks[resolution].iteritems() if v}
                        if not tracks[resolution]:
                            del tracks[resolution]
                            
                    #Compress speed
                    speed = store['Data']['Speed']
                    for resolution in speed.keys():
                        speed[resolution] = {k: int(v // compress_multplier)
                                             for k, v in speed[resolution].iteritems()}
                        speed[resolution] = {k: v for k, v in speed[resolution].iteritems() if v}
                        if not speed[resolution]:
                            del speed[resolution]
                            
                    #Compress combined
                    combined = store['Data']['Speed']
                    for resolution in combined.keys():
                        combined[resolution] = {k: int(v // compress_multplier)
                                                for k, v in combined[resolution].iteritems()}
                        combined[resolution] = {k: v for k, v in combined[resolution].iteritems() if v}
                        if not combined[resolution]:
                            del combined[resolution]
                    store['Data']['Ticks']['Current'] //= compress_multplier
                    notify.queue(MOUSE_TRACK_COMPRESS_END)
                    notify.queue(QUEUE_SIZE, q_recv.qsize())
                
            #Increment the amount of time the script has been running for
            if 'Ticks' in received_data:
                store['Data']['Ticks']['Total'] += received_data['Ticks']
            store['Data']['Ticks']['Recorded'] += 1

            _notify_send(q_send, notify)
            
            
    except Exception as e:
        q_send.put(traceback.format_exc())
        return
