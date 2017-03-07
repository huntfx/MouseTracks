from __future__ import division
from mt_core import FILE, DataStore, RefreshRateLimiter, calculate_line
import win32api
import win32con
import time

import os

keys = {
    'F1': [win32con.VK_F1, False],
    'F2': [win32con.VK_F2, False],
    'F3': [win32con.VK_F3, False],
    'F4': [win32con.VK_F4, False],
    'F5': [win32con.VK_F5, False],
    'F6': [win32con.VK_F6, False],
    'F7': [win32con.VK_F7, False],
    'F8': [win32con.VK_F8, False],
    'F9': [win32con.VK_F9, False],
    'F10': [win32con.VK_F10, False],
    'F11': [win32con.VK_F11, False],
    'F12': [win32con.VK_F12, False],
    'F13': [win32con.VK_F13, False],
    'F14': [win32con.VK_F14, False],
    'F15': [win32con.VK_F15, False],
    'F16': [win32con.VK_F16, False],
    'F17': [win32con.VK_F17, False],
    'F18': [win32con.VK_F18, False],
    'F19': [win32con.VK_F19, False],
    'F20': [win32con.VK_F20, False],
    'F21': [win32con.VK_F21, False],
    'F22': [win32con.VK_F22, False],
    'F23': [win32con.VK_F23, False],
    'F24': [win32con.VK_F24, False],
    'LCTRL': [win32con.VK_LCONTROL, False],
    'RCTRL': [win32con.VK_RCONTROL, False],
    'LSHIFT': [win32con.VK_LSHIFT, False],
    'RSHIFT': [win32con.VK_RSHIFT, False],
    'LALT': [win32con.VK_LMENU, False],
    'RALT': [win32con.VK_RMENU, False],
    'LWIN': [win32con.VK_LWIN, False],
    'RWIN': [win32con.VK_RWIN, False],
    'ESC': [win32con.VK_ESCAPE, False],
    'HOME': [win32con.VK_HOME, False],
    'DELETE': [win32con.VK_DELETE, False],
    'RETURN': [win32con.VK_RETURN, False],
    'BACK': [win32con.VK_BACK, False],
    'TAB': [win32con.VK_TAB, False],
    'DIVIDE': [win32con.VK_DIVIDE, False],
    'DECIMAL': [win32con.VK_DECIMAL, False],
    'MULTIPLY': [win32con.VK_MULTIPLY, False],
    'SUBTRACT': [win32con.VK_SUBTRACT, False],
    'ADD': [win32con.VK_ADD, False],
    'INSERT': [win32con.VK_INSERT, False],
    'CLEAR': [win32con.VK_CLEAR, False],
    'CAPSLOCK': [win32con.VK_CAPITAL, False],
    'SCROLLLOCK': [win32con.VK_SCROLL, False],
    'NUMLOCK': [win32con.VK_NUMLOCK, False],
    'NUM0': [win32con.VK_NUMPAD0, False],
    'NUM1': [win32con.VK_NUMPAD1, False],
    'NUM2': [win32con.VK_NUMPAD2, False],
    'NUM3': [win32con.VK_NUMPAD3, False],
    'NUM4': [win32con.VK_NUMPAD4, False],
    'NUM5': [win32con.VK_NUMPAD5, False],
    'NUM6': [win32con.VK_NUMPAD6, False],
    'NUM7': [win32con.VK_NUMPAD7, False],
    'NUM8': [win32con.VK_NUMPAD8, False],
    'NUM9': [win32con.VK_NUMPAD9, False],
    'HOME': [win32con.VK_HOME, False],
    'END': [win32con.VK_END, False],
    'PGUP': [win32con.VK_PRIOR, False],
    'PGDOWN': [win32con.VK_NEXT, False],
    'PAUSE': [win32con.VK_PAUSE, False],
    'UP': [win32con.VK_UP, False],
    'DOWN': [win32con.VK_DOWN, False],
    'LEFT': [win32con.VK_LEFT, False],
    'RIGHT': [win32con.VK_RIGHT, False],
    'SPACE': [win32con.VK_SPACE, False],
    'UNDERSCORE': [189, False],
    'EQUALS': [187, False],
    'MENU': [93, False],
    'BACKSLASH': [220, False],
    'FORWARDSLASH': [191, False],
    'COLON': [186, False],
    'AT': [192, False],
    'HASH': [222, False],
    'LBRACKET': [219, False],
    'RBRACKET': [221, False],
    'TILDE': [223, False],
    'PERIOD': [190, False],
    'COMMA': [188, False],
}
for c in list('ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890'):
    keys[c] = [ord(c), False]

if __name__ == '__main__':
    try:
        device = win32api.EnumDisplayDevices()
        settings = win32api.EnumDisplaySettings(device.DeviceName, 0)
        refresh_rate = getattr(settings, 'DisplayFrequency')
        resolution = (win32api.GetSystemMetrics(0), win32api.GetSystemMetrics(1))


        frame_time = 1 / refresh_rate

        f = DataStore(FILE)


        save_frequency = 10             #Seconds between file saves
        heatmap_stop_after_afk = 1      #Seconds user can be AFK before the heatmap stops


        if 'MovementCounter' not in f.data:
            f.data['MovementCounter'] = 1

        _save_frequency = save_frequency * refresh_rate
        _heatmap_stop = heatmap_stop_after_afk * refresh_rate
        last_frame = None
        frames_not_moved = 0
        mouse_clicked = False
        mouse_buttons = (win32con.VK_LBUTTON, win32con.VK_MBUTTON, win32con.VK_RBUTTON)
        #afk_markers = [False, False, True]
        
        keyboard_afk = True
        mouse_afk = False
        
        print 'Starting mouse tracking.'

        i = 0
        while True:
            i += 1
            with RefreshRateLimiter(frame_time) as limiter:

                #Get cursor position
                try:
                    pos = win32api.GetCursorPos()
                    if mouse_afk:
                        print 'Cursor position has been detected again.'
                    mouse_afk = False
                except win32api.error:
                    #Usually means you're afk so slow down the script
                    if not mouse_afk:
                        print 'Error with getting cursor position.'
                    mouse_afk = True
                    time.sleep(2)
                    continue

                #Check for duplicate position
                if pos == last_frame:
                    frames_not_moved += 1
                elif frames_not_moved:
                    frames_not_moved = 0

                
                #Store position (heatmap)
                if frames_not_moved <= _heatmap_stop:
                    heatmap_afk = False
                    try:
                        f.data[resolution]['Location'][pos] += 1
                    except KeyError:
                        try:
                            f.data[resolution]['Location'][pos] = 1
                        except KeyError:
                            f.data[resolution] = {'Location':{pos: 1},
                                                  'Movement': {},
                                                  'Clicks': {},
                                                  'Points': {}}
                elif not heatmap_afk:
                    afk_seconds = _heatmap_stop // refresh_rate
                    print 'Stopping heatmap, user has been away for {} second{}.'.format(
                        afk_seconds, '' if afk_seconds == 1 else 's')
                    heatmap_afk = True

                #Store position (lines), and interpolate between points
                #print frames_not_moved
                if not frames_not_moved:
                    
                    #print f.data['MovementCounter'], max(f.data[resolution]['Movement'].values())

                    if f.data['MovementCounter'] > 7200 * refresh_rate:
                        print 'Condensing old data...'
                        f.data['MovementCounter'] = 1 + f.data['MovementCounter'] // 1.1
                        for res in f.data:
                            try:
                                f.data[res]['Movement'] = {k: v // 1.1 for k, v
                                    in f.data[res]['Movement'].iteritems()}
                            except (KeyError, TypeError):
                                pass
                            except:
                                print f.data[res]
                                raise IOError
                        print 'Finished condensing.'
                    
                    try:
                        f.data['MovementCounter'] += 1
                    except KeyError:
                        try:
                            f.data['MovementCounter'] = 1
                        except KeyError:
                            f.data = {'MovementCounter': 1}
                    pixel_value = f.data['MovementCounter']
                    
                    f.data[resolution]['Movement'][pos] = pixel_value
                    if not frames_not_moved and last_frame is not None:
                        for mid_coordinates in calculate_line(last_frame, pos):
                            f.data[resolution]['Movement'][mid_coordinates] = pixel_value
                    

                #Save mouse clicks
                if any(win32api.GetAsyncKeyState(button) for button in mouse_buttons):
                    if not mouse_clicked:
                        print 'Mouse button clicked.'
                        mouse_clicked = limiter.time
                        try:
                            f.data[resolution]['Clicks'][pos] += 1
                        except KeyError:
                            f.data[resolution]['Clicks'][pos] = 1
                    elif mouse_clicked > 0 and mouse_clicked + 1 < limiter.time:
                        mouse_clicked *= -1
                        print 'Mouse button being held.'
                else:
                    if mouse_clicked < 0 and mouse_clicked > 1 - limiter.time:
                        print 'Mouse button unclicked.'
                    mouse_clicked = False

                
                #Save keypresses
                for k in keys:
                    if win32api.GetAsyncKeyState(keys[k][0]):
                        if keys[k][1]:
                            pass
                        else:
                            print k
                            keys[k][1] = True
                            keyboard_afk = False
                            try:
                                f.data['Keys'][k] += 1
                            except KeyError:
                                try:
                                    f.data['Keys'][k] = 1
                                except KeyError:
                                    f.data['Keys'] = {k: 1}
                    elif keys[k][1]:
                        keys[k][1] = False
                        
                #Save file
                if not i % _save_frequency:
                    last_modified = os.path.getmtime(FILE)
                    away_time = int(round(frames_not_moved / refresh_rate))
                    if frames_not_moved > _save_frequency and keyboard_afk:
                        if last_modified < away_time:
                            print 'Skipping save, user has been away for {} second{}.'.format(
                                away_time, '' if away_time == 1 else 's')
                        else:
                            print 'User is away but last save possibly failed, trying again.'
                            f.save()
                    else:
                        f.save()
                        keyboard_afk = True
                    
                last_frame = pos
                
    except Exception as e:
        with open('error.txt', 'w') as f:
            f.write("{}\n".format(e))

