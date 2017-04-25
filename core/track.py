from __future__ import division
from functions import calculate_line, RunningPrograms
from messages import *
from files import load_program, save_program
from constants import CONFIG
import time
import sys


def background_process(q_recv, q_send):
    try:
        notify.queue(START_THREAD)
        q_send.put(notify.output())
        store = {'Data': load_program(),
                 'Programs': {'Class': RunningPrograms(),
                              'Current': None,
                              'Previous': None},
                 'Resolution': None}
        notify.queue(DATA_LOADED)
        q_send.put(notify.output())
        while True:
            received_data = q_recv.get()
            try:
                messages = _background_process(received_data, store)
            except Exception as e:
                q_send.put('{}: {}'.format(sys.exc_info()[0], e))
                return
            else:
                if messages:
                    q_send.put(messages)
    except Exception as e:
        q_send.put('{}: {}'.format(sys.exc_info()[0], e))


def _background_process(received_data, store):

    check_resolution = False
    if 'Save' in received_data:
        if save_program(store['Programs']['Current'], store['Data']):
            notify.queue(SAVE_SUCCESS)
        else:
            notify.queue(SAVE_FAIL)
    
    if 'Programs' in received_data:
        if received_data['Programs']:
            store['Programs']['Class'].reload_file()
        else:
            store['Programs']['Class'].refresh()
            store['Programs']['Current'] = store['Programs']['Class'].check()
            if store['Programs']['Current'] != store['Programs']['Previous']:

                if store['Programs']['Current'] is None:
                    notify.queue(PROGRAM_QUIT)
                else:
                    notify.queue(PROGRAM_STARTED, store['Programs']['Current'])
                    
                notify.queue(SAVE_START)
                check_resolution = True
                if save_program(store['Programs']['Previous'], store['Data']):
                    notify.queue(SAVE_SUCCESS)
                else:
                    notify.queue(SAVE_FAIL)
    
                store['Programs']['Previous'] = store['Programs']['Current']
                    
                store['Data'] = load_program(store['Programs']['Current'])
                if store['Data']['Count']:
                    notify.queue(DATA_LOADED)
                else:
                    notify.queue(DATA_NOTFOUND)                    


    if 'Resolution' in received_data:
        check_resolution = True
        store['Resolution'] = received_data['Resolution']

    if check_resolution:
        if store['Resolution'] not in store['Data']['Tracks']:
            store['Data']['Tracks'][store['Resolution']] = {}
            store['Data']['Clicks'][store['Resolution']] = {}
    
    if 'Keys' in received_data:
        for key in received_data['Keys']:
            try:
                store['Data']['Keys'][key] += 1
            except KeyError:
                store['Data']['Keys'][key] = 1

    if 'MouseClick' in received_data:
        try:
            store['Data']['Clicks'][store['Resolution']][received_data['MouseClick']] += 1
        except KeyError:
            store['Data']['Clicks'][store['Resolution']][received_data['MouseClick']] = 1

    if 'MouseMove' in received_data:
        start, end = received_data['MouseMove']
        if start is None:
            mouse_coordinates = [end]
        else:
            mouse_coordinates = [start, end] + calculate_line(start, end)
        for pixel in mouse_coordinates:
            store['Data']['Tracks'][store['Resolution']][pixel] = store['Data']['Count']
                
        store['Data']['Count'] += 1
        compress_frequency = CONFIG.data['CompressTracks']['Frequency']
        compress_multplier = CONFIG.data['CompressTracks']['Multiplier']
        compress_limit = compress_frequency * CONFIG.data['Main']['UpdatesPerSecond']
        if store['Data']['Count'] > compress_limit:
            notify.queue(MOUSE_TRACK_COMPRESS_START)
            for resolution in store['Data']['Tracks'].keys():
                store['Data']['Tracks'][resolution] = {k: v // compress_multplier for k, v in
                                                store['Data']['Tracks'][resolution].iteritems()}
                store['Data']['Count'] //= compress_multplier
            notify.queue(MOUSE_TRACK_COMPRESS_END)

    
    if 'Ticks' in received_data:
        store['Data']['Ticks'] += received_data['Ticks']

    notify_output = notify.output()
    if notify_output:
        return notify_output
