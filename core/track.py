from __future__ import division
from functions import calculate_line, RunningPrograms, find_distance
from messages import *
from files import load_program, save_program
from constants import CONFIG
import time
import sys


def _notify_send(q_send, notify):
    """Wrapper to the notify class to send non empty values."""
    output = notify.output()
    if output:
        q_send.put(output)


def _save_wrapper(q_send, store):
    notify.queue(SAVE_START)
    _notify_send(q_send, notify)
    saved = False
    for i in xrange(CONFIG.data['Save']['MaximumAttempts']):
        if save_program(store['Programs']['Current'], store['Data']):
            notify.queue(SAVE_SUCCESS)
            _notify_send(q_send, notify)
            saved = True
            break
        else:
            if CONFIG.data['Save']['MaximumAttempts'] == 1:
                notify.queue(SAVE_FAIL)
                return
            notify.queue(SAVE_FAIL_RETRY, CONFIG.data['Save']['WaitAfterFail'],
                         i, CONFIG.data['Save']['MaximumAttempts'])
            _notify_send(q_send, notify)
            time.sleep(CONFIG.data['Save']['WaitAfterFail'])
    if not saved:
        notify.queue(SAVE_FAIL_END)


def background_process(q_recv, q_send):
    try:
        notify.queue(START_THREAD)
        _notify_send(q_send, notify)
        
        store = {'Data': load_program(),
                 'Programs': {'Class': RunningPrograms(),
                              'Current': None,
                              'Previous': None},
                 'Resolution': None}
        
        notify.queue(DATA_LOADED)
        _notify_send(q_send, notify)
        
        while True:
            received_data = q_recv.get()
            try:
                messages = _background_process(q_send, received_data, store)
            except Exception as e:
                q_send.put('Error: {}: line {}, {}'.format(e, sys.exc_info()[2].tb_lineno, sys.exc_info()[0]))
                return
            
    except Exception as e:
        q_send.put('{}: {}'.format(sys.exc_info()[0], e))


def _background_process(q_send, received_data, store):

    check_resolution = False
    if 'Save' in received_data:
        _save_wrapper(q_send, store)

    if 'Programs' in received_data:
        if received_data['Programs']:
            store['Programs']['Class'].reload_file()
            notify.queue(PROGRAM_RELOAD)
        else:
            store['Programs']['Class'].refresh()
            store['Programs']['Current'] = store['Programs']['Class'].check()
            if store['Programs']['Current'] != store['Programs']['Previous']:

                if store['Programs']['Current'] is None:
                    notify.queue(PROGRAM_QUIT)
                else:
                    notify.queue(PROGRAM_STARTED, store['Programs']['Current'])
                    
                notify.queue(SAVE_START)
                _notify_send(q_send, notify)
                
                check_resolution = True
                _save_wrapper(q_send, store)
    
                store['Programs']['Previous'] = store['Programs']['Current']
                    
                store['Data'] = load_program(store['Programs']['Current'])
                if store['Data']['Count']:
                    notify.queue(DATA_LOADED)
                else:
                    notify.queue(DATA_NOTFOUND)
        _notify_send(q_send, notify)


    if 'Resolution' in received_data:
        check_resolution = True
        store['Resolution'] = received_data['Resolution']

    if check_resolution:
        if store['Resolution'] not in store['Data']['Tracks']:
            store['Data']['Tracks'][store['Resolution']] = {}
        if store['Resolution'] not in store['Data']['Clicks']:
            store['Data']['Clicks'][store['Resolution']] = {}
        if store['Resolution'] not in store['Data']['Speed']:
            store['Data']['Speed'][store['Resolution']] = {}
    
    if 'Keys' in received_data:
        for key in received_data['Keys']:
            try:
                store['Data']['Keys'][key] += 1
            except KeyError:
                store['Data']['Keys'][key] = 1

    if 'MouseClick' in received_data:
        for mouse_click in received_data['MouseClick']:
            try:
                store['Data']['Clicks'][store['Resolution']][mouse_click] += 1
            except KeyError:
                store['Data']['Clicks'][store['Resolution']][mouse_click] = 1

    if 'MouseMove' in received_data:
        start, end = received_data['MouseMove']
        distance = find_distance(end, start)
        
        if start is None:
            mouse_coordinates = [end]
        else:
            mouse_coordinates = [start, end] + calculate_line(start, end)

            
        for pixel in mouse_coordinates:
            store['Data']['Tracks'][store['Resolution']][pixel] = store['Data']['Count']

            try:
                if store['Data']['Speed'][store['Resolution']][pixel] < distance:
                    raise KeyError()
            except KeyError:
                store['Data']['Speed'][store['Resolution']][pixel] = distance
                
        store['Data']['Count'] += 1
        
        #Compress tracks if the count gets too high
        compress_frequency = CONFIG.data['CompressTracks']['Frequency']
        compress_multplier = CONFIG.data['CompressTracks']['Multiplier']
        compress_limit = compress_frequency * CONFIG.data['Main']['UpdatesPerSecond']
        if store['Data']['Count'] > compress_limit:
            
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
            store['Data']['Count'] //= compress_multplier
            notify.queue(MOUSE_TRACK_COMPRESS_END)

    
    if 'Ticks' in received_data:
        store['Data']['Ticks'] += received_data['Ticks']

    _notify_send(q_send, notify)
