from __future__ import division, absolute_import
from threading import Thread
from multiprocessing import Process, Queue
import sys
import os
import time

from core.compatibility import input, range
from core.constants import DEFAULT_PATH, format_file_path
from core.messages import print_override
from core.notify import *
from core.os import get_running_processes
    
    
def error_output(trace):
    """Any errors are sent to here."""
    file_name = format_file_path('{}\\error.txt'.format(DEFAULT_PATH))
    with open(file_name, 'w') as f:
        f.write(trace)
    print_override(trace)
    input('Press enter to close.')
    sys.exit()


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

        
def value_select(selection, default, start=0):
    """Convert a list of numbers into a range of True/False.
    If no input is given, default will be returned,
    otherwise all values not given will be False.
    """
    result = []
    if selection:
        for i, default_value in enumerate(default):
            result.append(i + start in selection)
        return result
    return list(default)
