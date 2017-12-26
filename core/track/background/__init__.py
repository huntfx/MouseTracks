"""
This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""
#The background process does all the heavy lifting and is not required to be in realtime

from __future__ import division, absolute_import

import time
import traceback

import core.numpy as numpy
from core.track.background.helper import *
from core.applications import RunningApplications
from core.compatibility import range, get_items
from core.config import CONFIG
from core.constants import MAX_INT, DISABLE_TRACKING, IGNORE_TRACKING, UPDATES_PER_SECOND
from core.files import LoadData, save_data, prepare_file
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
        last_app_resolution = None
            
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
                    
                    if current_app is None:
                        application_resolution = None
                    
                    else:
                        application_resolution = (running_apps.focus.rect(), running_apps.focus.resolution())
                        
                        if current_app == previous_app:
                            if application_resolution[1] != last_resolution:
                                NOTIFY(APPLICATION_RESIZE, last_resolution, application_resolution[1])
                            elif application_resolution[0] != last_coordinates:
                                NOTIFY(APPLICATION_MOVE, last_coordinates, application_resolution[0])
                        else:
                            NOTIFY(APPLICATION_RESOLUTION, application_resolution[1])
                            
                        last_coordinates, last_resolution = application_resolution
                    
                    if last_app_resolution != application_resolution:
                        send['ApplicationResolution'] = last_app_resolution = application_resolution
                
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
            
            update_resolution = False
            
            #Check for new program loaded
            if 'Program' in received_data:
                current_program = received_data['Program']
                
                if current_program != store['LastProgram']:
                    update_resolution = True
                    
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
                    start, end = received_data['MouseMove']
                    store['Data']['HistoryAnimation']['Tracks'][-1].append(end)
                
                #Compress tracks if the count gets too high
                max_track_value = CONFIG['Advanced']['CompressTrackMax']
                if not max_track_value:
                    max_track_value = MAX_INT
                
                if store['Data']['Ticks']['Tracks'] > max_track_value:
                    NOTIFY(TRACK_COMPRESS_START, 'track')
                    NOTIFY.send(q_send)
                    
                    compress_tracks(store, CONFIG['Advanced']['CompressTrackAmount'])
                    
                    NOTIFY(TRACK_COMPRESS_END, 'track')
                    try:
                        NOTIFY(QUEUE_SIZE, q_recv.qsize())
                    except NotImplementedError:
                        pass
                
            #Record mouse clicks
            if 'MouseClick' in received_data:
                store['ActivitySinceLastSave'] = True
                record_click_single(store, received_data['MouseClick'])
                    
            #Record double clicks
            if 'DoubleClick' in received_data:
                store['ActivitySinceLastSave'] = True
                record_click_double(store, received_data['DoubleClick'])
            
            #Trim the history list if too long
            if 'HistoryCheck' in received_data and CONFIG['Main']['HistoryLength']:
                max_length = CONFIG['Main']['HistoryLength'] * UPDATES_PER_SECOND
                history_trim(store, max_length)
                        
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
