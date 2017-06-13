from __future__ import division
from threading import Thread
from multiprocessing import Process, Queue
from sys import version_info
import os
import time

from core.os import get_cursor_pos, get_running_processes

if version_info.major == 2:
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
    

def get_items(d):
    """As Python 2 and 3 have different ways of getting items,
    any attempt should be wrapped in this function.
    """
    if version_info.major == 2:
        return d.iteritems()
    else:
        return d.items()


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
            self.cache.append(self.calculate_colour(i * self._step_size))
            
    def __getitem__(self, n):
        value_index = int(n / self._step_size)
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
    def __init__(self, program_list='Program List.txt', list_only=False):
        if not list_only:
            self.refresh()
        self.program_list = program_list
        self.reload_file()

    def reload_file(self):
        try:
            with open(self.program_list, 'r') as f:
                lines = f.readlines()
        except IOError:
            with open(self.program_list, 'w') as f:
                lines = ['# Type any programs you want to be tracked here.',
                         '# It is done in the format "CaseSensitive.exe: name"'
                         ', where two can have the same name.',
                         '# If no name is given it\'ll default to the filename.',
                         '# In the case of multiple programs loaded at the same time'
                         ', the program will try select the most recently loaded.',
                         '',
                         'game.exe: Name']
                f.write('\r\n'.join(lines))

        programs = tuple(i.strip() for i in lines)
        self.programs = {}
        program_type = None #1: windows, 2: linux, 3: mac
        for program_info in programs:
            if not program_info or program_info[0] in ('#', ';', '//'):
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
            
            self.programs[program_name] = friendly_name
            
    def refresh(self):
        self.processes = get_running_processes()
        
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


class SimpleConfig(object):
    def __init__(self, file_name, default_data, group_order=None):
        self.file_name = file_name
        self._default_data = default_data
        self.default_data = {}
        self.order = list(group_order) if group_order is not None else []
        for group, data in self._default_data.iteritems():
            self.default_data[group] = self._default_data[group]
        self.load()
    
    def load(self):
        try:
            with open(self.file_name, 'r') as f:
                config_lines = [i.strip() for i in f.readlines()]
        except IOError:
            config_lines = []
        
        #Read user values
        config_data = {}
        for line in config_lines:
            if not line:
                continue
            if line.startswith('['):
                current_group = line[1:].split(']', 1)[0]
                config_data[current_group] = {}
            elif line[0] in (';', '/', '#'):
                pass
            else:
                name, value = [i.strip() for i in line.split('=')]
                value = value.replace('#', ';').replace('//', ';').split(';', 1)[0]
                try:
                    default_value, default_type = self.default_data[current_group][name][:2]
                except KeyError:
                    pass
                else:
                    if default_type == bool:
                        if value.lower() in ('0', 'false'):
                            value = False
                        elif value.lower() in ('1', 'true'):
                            value = True
                        else:
                            value = default_value
                            
                    elif default_type == int:
                        if '.' in value:
                            value = value.split('.')[0]
                        try:
                            value = int(value)
                        except ValueError:
                            value = default_value
                            
                    elif default_type == str:
                        value = str(value).rstrip()
                        
                    else:
                        value = default_type(value)
                    
                    #Handle min/max values
                    if default_type in (int, float):
                        no_text = [i for i in self.default_data[current_group][name] if not isinstance(i, str)]
                        if len(no_text) >= 3:
                            if no_text[2] is not None and no_text[2] > value:
                                value = no_text[2]
                            elif len(no_text) >= 4:
                                if no_text[3] is not None and no_text[3] < value:
                                    value = no_text[3]
                
                config_data[current_group][name] = value
        
        #Add any remaining default values
        for group, variables in get_items(self.default_data):
            for variable, defaults in get_items(variables):
                try:
                    config_data[group][variable]
                except KeyError:
                    try:
                        config_data[group][variable] = defaults[0]
                    except KeyError:
                        config_data[group] = {variable: defaults[0]}

        self.data = config_data        
        return self.data

    def save(self):
    
        extra_items = list(set(self._default_data.keys()) - set(self.order))
        
        output = []
        for group in self.order + extra_items:
            variables = self._default_data[group]
            if output:
                output.append('')
            output.append('[{}]'.format(group))
            if '__note__' in variables:
                for note in variables.pop('__note__'):
                    output.append('// {}'.format(note))
            for variable in sorted(variables.keys()):
                defaults = variables[variable]
                try:
                    value = self.data[group][variable]
                except KeyError:
                    value = defaults[0]
                output.append('{} = {}'.format(variable, value))
                try:
                    if isinstance(defaults[-1], str) and defaults[-1]:
                        output[-1] += '    // {}'.format(defaults[-1])
                except IndexError:
                    pass
        with open(self.file_name, 'w') as f:
            f.write('\n'.join(output))

    def __getitem__(self, item):
        return self.data[item]
    

def find_distance(p1, p2=None, decimal=False):
    """Find the distance between two (x, y) coordinates."""
    if p2 is None:
        return (0, 0.0)[decimal]
    distance = ((p2[0] - p1[0]) ** 2 + (p2[1] - p1[1]) ** 2) ** 0.5
    if decimal:
        return distance
    return int(round(distance))
