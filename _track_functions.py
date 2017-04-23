from __future__ import division
from threading import Thread
import time
import os
from _track_windows import get_cursor_pos
from multiprocessing import Process, Queue


class RefreshRateLimiter(object):
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
            for i in xrange(1, difference[1]):
                result.append((start[0], start[1] + i))
        elif difference[1] < -1:
            for i in xrange(1, -difference[1]):
                result.append((start[0], start[1] - i))
        return result
    if not difference[1]:
        if difference[0] > 1:
            for i in xrange(1, difference[0]):
                result.append((start[0] + i, start[1]))
        elif difference[0] < -1:
            for i in xrange(1, -difference[0]):
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
    def __init__(self, amount, colours):
        self.amount = amount - 1
        self.colours = colours
        self._colour_len = len(colours) - 1
        if isinstance(colours, (tuple, list)):
            if all(isinstance(i, (tuple, list)) for i in colours):
                if len(set(len(i) for i in colours)) == 1:
                    return
        raise TypeError('invalid list of colours')

    def get_colour(self, n, as_int=True):
        n = min(self.amount, max(n, 0))
        
        value = (n * self._colour_len) / self.amount
        base_value = int(value)

        base_colour = self.colours[base_value]
        try:
            mix_colour = self.colours[base_value + 1]
        except IndexError:
            mix_colour = base_colour

        difference = value - base_value
        difference_reverse = 1 - difference
        base_colour = [i * difference_reverse for i in base_colour]
        mix_colour = [i * difference for i in mix_colour]
        if as_int:
            return tuple(int(i + j) for i, j in zip(base_colour, mix_colour))
        else:
            return tuple(i + j for i, j in zip(base_colour, mix_colour))


class RunningPrograms(object):
    def __init__(self, program_list='Program List.txt'):
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
        for program_info in programs:
            print program_info
            if not program_info or program_info[0] in ('#', ';', '//'):
                continue
            try:
                exe_name, friendly_name = program_info.split('.exe', 1)
                if not friendly_name:
                    raise ValueError()
            except ValueError:
                if '.exe' in program_info:
                    exe_name = program_info.split('.exe')[0]
                    friendly_name = ':' + exe_name
                else:
                    continue
            friendly_name = friendly_name.split(':', 1)[1].strip()
            exe_name = exe_name.strip() + '.exe'
            self.programs[exe_name] = friendly_name
            
            
    def refresh(self):
        task_list = os.popen("tasklist").read().splitlines()
        self.processes = {line.strip().split('.exe')[0] + '.exe': i
                          for i, line in enumerate(task_list) if '.exe' in line}
        
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
