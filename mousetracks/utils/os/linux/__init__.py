"""This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""
#Linux functions that don't require any special imports
#Thanks to /u/Astrrum for helping, still needs a lot of work

from __future__ import absolute_import

import subprocess
import re

try:
    from .xlib import *
except ImportError:
    pass


def get_running_processes():
    pids = []
    program_list = subprocess.Popen('ps -d', shell=True, stdout=subprocess.PIPE).communicate()[0]
    for line in program_list.splitlines():
        pids.append(line.decode())
    output = {line.rsplit()[-1]: line.rsplit()[0] for line in pids}
    return output


def get_refresh_rate():
    raw_rate = subprocess.Popen('xrandr | grep "\*" | cut -d" " -f9',shell=True, stdout=subprocess.PIPE).communicate()[0]
    refresh_rate = re.search('\d+\.\d+', raw_rate.decode()).group()
    if refresh_rate:
        return int(refresh_rate)
    else:
        return None