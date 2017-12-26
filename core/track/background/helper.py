"""
This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""

from __future__ import absolute_import

from core.compatibility import get_items
from core.maths import calculate_line, find_distance
from core.os import MULTI_MONITOR
import core.numpy as numpy


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
        store['Data']['Resolution'][resolution]['Clicks']['All'][click_type][mouse_button][y][x] += 1
        store['Data']['Resolution'][resolution]['Clicks']['Session'][click_type][mouse_button][y][x] += 1


def record_click_single(store, received_data):
    return _record_click(store, received_data, 'Single')


def record_click_double(store, received_data):
    return _record_click(store, received_data, 'Single')
    

def compress_tracks(store, multiplier):
    
    compress_multplier = CONFIG['Advanced']['CompressTrackAmount']
    
    for resolution, maps in get_items(store['Data']['Resolution']):
        maps['Tracks'] = numpy.divide(maps['Tracks'], compress_multplier, as_int=True)
            
    store['Data']['Ticks']['Tracks'] //= compress_multplier
    store['Data']['Ticks']['Tracks'] = int(store['Data']['Ticks']['Tracks'])
    store['Data']['Ticks']['Session']['Tracks'] //= compress_multplier
    store['Data']['Ticks']['Session']['Tracks'] = int(store['Data']['Ticks']['Session']['Tracks'])
    
    
def _record_gamepad(store, received_data, press_type):
    for button_id in received_data['GamepadButtonPress']:
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
        

def record_key_held(store, received_data):
    for key in received_data:
        _record_keypress(store['Data']['Keys'], 'Held', key)
        
        
def record_mouse_move(store, received_data):

    store['ActivitySinceLastSave'] = True
    resolution = 0
    _resolution = -1
    
    start, end = received_data
    
    #Store total distance travelled
    distance = find_distance(end, start)
    store['Data']['Distance']['Tracks'] += distance
    
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