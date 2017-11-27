"""
This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""

from __future__ import absolute_import

import os

from core.compatibility import PYTHON_VERSION

try:
    from core.os.windows.pywin32 import *
except ImportError:
    from core.os.windows.ctypes import *


def read_env_var(text):
    """Detect if text is an environment variable and read it.
    Returns:
        Value/None if successful or not.
    """
    if not text:
        return None
    if text[0] == text[-1] == '%':
        return os.getenv(text[1:-1])
    return None


def get_running_processes():
    """Return a dictionary of running processes, with their ID as the value.
    The ID is used to determine which process was most recently loaded.
    """
    task_list = os.popen("tasklist /NH /FO CSV").read().splitlines()
    
    running_processes = {}
    for i, task_raw in enumerate(task_list):
        image = task_raw.split(',', 1)[0][1:-1]
        if '.' in image:
            running_processes[image] = i
    return running_processes