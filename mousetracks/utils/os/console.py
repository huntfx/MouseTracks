"""This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""
#Control over the Python console
#Used for launching a new elevated process

from __future__ import absolute_import

import os
import sys

from ._load_from_os import *


ELEVATE = 'ElevateProgram'


def _launch(add_arguments=[], remove_arguments=[], visible=True):
    """Launch a new instance of python with arguments provided."""
    if isinstance(add_arguments, str):
        add_arguments = [add_arguments]
    if isinstance(remove_arguments, str):
        remove_arguments = [remove_arguments]
    script = os.path.abspath(sys.argv[0])
    params = ' '.join([script] + [i for i in sys.argv[1:] if i not in remove_arguments] + list(add_arguments))
    return launch_console(params=params, visible=visible)

    
def has_been_elevated():
    return ELEVATE in sys.argv
    

def elevate(visible=True):
    """Attempt to elevate the current script and quit the original if successful.
    Ignore if being debugged. Ideally this part needs to figure out when it is acceptable to elevate.
    """
    if is_elevated() or has_been_elevated() or sys.argv[0].endswith('visualstudio_py_launcher.py'):
        return True
    
    if _launch(visible=visible, add_arguments=[ELEVATE]):
        sys.exit(0)
    
    return False


def new(*args):
    _launch(visible=True, add_arguments=list(args), remove_arguments=[ELEVATE])


def is_set(*args):
    for arg in args:
        if arg in sys.argv:
            return True