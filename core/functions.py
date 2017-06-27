from __future__ import division
from threading import Thread
from multiprocessing import Process, Queue
import sys
import os
import time

from core.constants import PROGRAM_LIST_URL, CONFIG, PROGRAM_LIST_PATH
from core.online import get_url_contents
from core.os import get_cursor_pos, get_running_processes
from core.messages import *

if sys.version_info.major == 2:
    range = xrange

    
def print_override(text):
    """Send everything here to print, so that it can easily be edited.
    Defaults to Python 3 version as it'll refuse to even run the script otherwise.
    """
    print(text)
        
    
def error_output(trace, file_name='error.txt'):
    """Any errors are sent to here."""
    with open(file_name, 'w') as f:
        f.write(trace)
    print_override(trace)
    time.sleep(5)


class RefreshRateLimiter(object):
    """Limit the loop to a fixed updates per second.
    It works by detecting how long a frame should be,
    and comparing it to how long it's already taken.
    """
    def __init__(self, ticks):
        self.time = time.time()
        self.frame_time = 1 / ticks
        self.pos = get_cursor_pos()

    def mouse_pos(self):
        return self.pos

    def __enter__(self):
        return self

    def __exit__(self, *args):
        time_difference = time.time() - self.time
        time.sleep(max(0, self.frame_time - time_difference))


def calculate_line(start, end):
    """Calculates path in terms of pixels between two points.
    Does not include the start and end point.
    """
    result = []
    
    #Return nothing if the two points are the same
    if start == end:
        return result

    difference = (end[0] - start[0], end[1] - start[1])
    
    #Check if the points are on the same axis
    if not difference[0]:
        if difference[1] > 1:
            for i in range(1, difference[1]):
                result.append((start[0], start[1] + i))
        elif difference[1] < -1:
            for i in range(1, -difference[1]):
                result.append((start[0], start[1] - i))
        return result
    if not difference[1]:
        if difference[0] > 1:
            for i in range(1, difference[0]):
                result.append((start[0] + i, start[1]))
        elif difference[0] < -1:
            for i in range(1, -difference[0]):
                result.append((start[0] - i, start[1]))
        return result
    
    slope = difference[1] / difference[0]
    
    count = slope
    x, y = start
    x_neg = -1 if difference[0] < 0 else 1
    y_neg = -1 if difference[1] < 0 else 1
    i = 0
    while True:
        i += 1
        if i > 100000:
            raise ValueError('failed to find path between {}, {}'.format(start, end))
        
        #If y > x and both pos or both neg
        if slope >= 1 or slope <= 1:
            if count >= 1:
                y += y_neg
                count -= 1
            elif count <= -1:
                y += y_neg
                count += 1
            else:
                x += x_neg
                count += slope
                
        # If y < x and both pos or both neg
        elif slope:
            if count >= 1:
                y += y_neg
                count -= 1
            elif count <= -1:
                y += y_neg
                count += 1
            if -1 <= count <= 1:
                x += x_neg
            count += slope
            
        coordinate = (x, y)
        if coordinate == end:
            return result
        result.append(coordinate)
        
        #Quick fix since values such as x(-57, -53) y(-22, -94) are one off
        #and I can't figure out how to make it work
        if end[0] in (x-1, x, x+1) and end[1] in (y-1, y, y+1):
            return result


class ColourRange(object):
    """Make a transition between colours."""
    def __init__(self, min_amount, max_amount, colours, offset=0, loop=False):

        self.amount = (min_amount, max_amount)
        self.amount_diff = max_amount - min_amount
        self.colours = colours
        self.offset = offset
        self.loop = loop
        self._len = len(colours)
        self._len_m = self._len - 1

        self._step_max = 255 * self._len
        self._step_size = self.amount_diff / self._step_max
        
        #Cache results for quick access
        self.cache = []
        for i in range(self._step_max + 1):
            self.cache.append(self.calculate_colour(self.amount[0] + i * self._step_size))
            
    def __getitem__(self, n):
        value_index = int((n - self.amount[0]) / self._step_size)
        if self.loop:
            if value_index != self._step_max:
                return self.cache[value_index % self._step_max]
        return self.cache[min(max(0, value_index), self._step_max)]
    
    def calculate_colour(self, n, as_int=True):
        offset = (n + self.offset - self.amount[0]) / self.amount_diff
        index_f = self._len_m * offset

        #Calculate the indexes of colours to mix
        index_base = int(index_f)
        index_mix = index_base + 1
        if self.loop:
            index_base %= self._len
            index_mix %= self._len
        else:
            index_base = max(min(index_base, self._len_m), 0)
            index_mix = max(min(index_mix, self._len_m), 0)

        #Mix colours
        base_colour = self.colours[index_base]
        mix_colour = self.colours[index_mix]
        mix_ratio = max(min(index_f - index_base, 1), 0)
        mix_ratio_r = 1 - mix_ratio

        #Generate as tuple
        if as_int:
            return tuple(int(i * mix_ratio_r + j * mix_ratio)
                         for i, j in zip(base_colour, mix_colour))
        else:
            return tuple(i * mix_ratio_r + j * mix_ratio for i, j in zip(base_colour, mix_colour))


class RunningPrograms(object):

    HELP_TEXT = ['// Type any apps you want to be tracked here.',
                 '// Two separate apps may have the same name, and will be tracked under the same file.',
                 '// Put each app on a new line, in the format "Game.exe: Name".'
                 ' The executable file is case sensitive.',
                 '// Alternatively if the app is already named with the correct name'
                 ', "Game.exe" by itself will use "Game" as its name.',
                 '']

    def __init__(self, program_list=PROGRAM_LIST_PATH, list_only=False, queue=None):
        self.q = queue
        if not list_only:
            self.refresh()
        self.program_list = program_list
        self.reload_file()

    def reload_file(self):
        try:
            with open(self.program_list, 'r') as f:
                lines = f.readlines()
        except IOError:
            lines = self.HELP_TEXT + ['// game.exe: Name']
            with open(self.program_list, 'w') as f:
                f.write('\r\n'.join(lines))

        self.programs = self._format_programs(lines)
        
        #Download from the internet and combine with the current list
        internet_allowed = CONFIG['Internet']['Enable']
        last_updated = CONFIG['SavedSettings']['ProgramListUpdate']
        update_frequency = CONFIG['Internet']['UpdatePrograms']
        
        if internet_allowed and (not self.programs 
                                 or not last_updated 
                                 or last_updated < time.time() - update_frequency):
        
            if self.q is not None:
                NOTIFY(PROGRAM_UPDATE_START)
                NOTIFY.send(self.q)
                
            download_program_list = get_url_contents(PROGRAM_LIST_URL)
            if download_program_list is not None:
                downloaded_programs = self._format_programs(download_program_list)
                for k, v in downloaded_programs.iteritems():
                    if k not in self.programs:
                        self.programs[k] = v
                CONFIG['SavedSettings']['ProgramListUpdate'] = int(time.time())
                CONFIG.save()
                self.save_file()
                
                if self.q is not None:
                    NOTIFY(PROGRAM_UPDATE_END_SUCCESS)
                    NOTIFY.send(self.q)
            else:
                if self.q is not None:
                    NOTIFY(PROGRAM_UPDATE_END_FAIL)
                    NOTIFY.send(self.q)
                
    def _format_programs(self, program_lines):
    
        program_dict = {}
        for program_info in program_lines:
        
            program_info = program_info.strip()
            
            if not program_info or any(program_info.startswith(i) for i in ('#', ';', '/')):
                continue
            
            program_lc = program_info.lower()
            if '.exe' in program_lc:
                ext_len = len(program_lc.split('.exe')[0])
                program_name = program_info[:ext_len + 4]
            elif '.app' in program_lc:
                ext_len = len(program_lc.split('.app')[0])
                program_name = program_info[:ext_len + 4]
            else:
                continue
                
            try:
                friendly_name = program_info[ext_len:].split(':', 1)[1].strip()
            except IndexError:
                friendly_name = program_info[:ext_len]
            
            program_dict[program_name] = friendly_name
        
        return program_dict
        
    def refresh(self):
        self.processes = get_running_processes()
    
    def save_file(self):
        lines = self.HELP_TEXT
        
        sorted_program_list = sorted(self.programs.keys(), key=lambda s: s.lower())
        for program_info in sorted_program_list:
            friendly_name = self.programs[program_info]
        
            if not program_info or any(program_info.startswith(i) for i in ('#', ';', '/')):
                continue
            
            program_lc = program_info.lower()
            if '.exe' in program_lc:
                ext_len = len(program_lc.split('.exe')[0])
                program_name = program_info[:ext_len]
            elif '.app' in program_lc:
                ext_len = len(program_lc.split('.app')[0])
                program_name = program_info[:ext_len]
            else:
                continue
            
            if program_name == friendly_name:
                lines.append(program_info)
            else:
                lines.append('{}: {}'.format(program_info, friendly_name))
        
        with open(self.program_list, 'w') as f:
            f.write('\r\n'.join(lines))
    
    def check(self):
        """Check for any programs in the list that are currently loaded.
        Choose the one with the highest ID as it'll likely be the most recent one.
        """
        matching_programs = {}
        for program in self.programs:
            if program in self.processes:
                matching_programs[self.processes[program]] = program
        if not matching_programs:
            return None
        latest_program = matching_programs[max(matching_programs.keys())]
        return (self.programs[latest_program], latest_program)
    

def find_distance(p1, p2=None, decimal=False):
    """Find the distance between two (x, y) coordinates."""
    if p2 is None:
        return (0, 0.0)[decimal]
    distance = ((p2[0] - p1[0]) ** 2 + (p2[1] - p1[1]) ** 2) ** 0.5
    if decimal:
        return distance
    return int(round(distance))


_LENGTH = (
    ('second', 1, 60, 2),
    ('minute', 60, 60, None),
    ('hour', 60 * 60, 24, None),
    ('day', 60 * 60 * 24, 7, None),
    ('week', 60 * 60 * 24 * 7, 52, None),
    ('year', 60 * 60 * 24 * 365, None, None)
)


def ticks_to_seconds(amount, tick_rate, output_length=2, allow_decimals=True):  

    output = []
    time_elapsed = amount / tick_rate
    for name, length, limit, decimals in _LENGTH[::-1]:
        if decimals is None or not allow_decimals:
            current = int(time_elapsed // length)
        else:
            current = round(time_elapsed / length, decimals)
        if limit is not None:
            current %= limit

        if current:
            output.append('{} {}{}'.format(current, name, '' if current == 1 else 's'))
            if len(output) == output_length:
                break
    
    if not output:
        output.append('{} {}s'.format(current, name))
    
    if len(output) > 1:
        result = ' and '.join((', '.join(output[:-1]), output[-1]))
    else:
        result = output[-1]

    return result
    

def simple_bit_mask(selection, size, default_all=True):
    """Turn a range of numbers into True and False.
    For example, [1, 3, 4] would result in [True, False, True, True].
    I'm aware it's probably a bit overkill, kinda liked the idea though.
    """
    
    #Calculate total
    total = 0
    for n in selection:
        try:
            total += pow(2, int(n) - 1)
        except ValueError:
            pass
    
    #Convert to True or False
    values = map(bool, list(map(int, str(bin(total))[2:]))[::-1])
    size_difference = max(0, size - len(values))
    if size_difference:
        values += [False] * size_difference
    
    #Set to use everything if an empty selection is given
    if default_all:
        if not any(values):
            values = [True] * size
    
    return values
