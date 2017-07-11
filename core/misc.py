from __future__ import division, absolute_import
from threading import Thread
from multiprocessing import Process, Queue
import sys
import os
import time

from core.basic import format_file_path, get_python_version
from core.constants import DEFAULT_PATH
from core.messages import print_override
from core.notify import *
from core.os import get_running_processes
        
if get_python_version() != 2:
    raw_input = input
    
    
def error_output(trace):
    """Any errors are sent to here."""
    file_name = format_file_path('{}\\error.txt'.format(DEFAULT_PATH))
    with open(file_name, 'w') as f:
        f.write(trace)
    print_override(trace)
    raw_input('Press enter to close.')


class RefreshRateLimiter(object):
    """Limit the loop to a fixed updates per second.
    It works by detecting how long a frame should be,
    and comparing it to how long it's already taken.
    """
    def __init__(self, ticks):
        self.time = time.time()
        self.frame_time = 1 / ticks

    def __enter__(self):
        return self

    def __exit__(self, *args):
        time_difference = time.time() - self.time
        time.sleep(max(0, self.frame_time - time_difference))
    

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
