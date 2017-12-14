"""
This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""
"""
Requirements:
Launching programs:
    Launch program
    Check if that program is already loaded
    Save PID of launched programs
Terminating programs:
    Close PID
    Check if a program is loaded before terminating (maybe not worth it as the new program won't have the old PID)
Wait:
    Simply wait before continuing
Keypress
MouseClick
MouseMove
Files:
    Move/copy existing file
    Wildcard at either side of filename, only 1 allowed
    If wildcard in new filename copies from original filename
    Use original filename if new location is a folder
    Allow sorting to get the highest/lowest matching file
    Allow offset when sorting
        COPY C:/image* SORTED MAX OFFSET 0 D:/backup/
        COPY C:/image* SORTED MAX OFFSET 0 D:/backup/image*
"""
from __future__ import absolute_import

import time
import os

from core.applications import RunningApplications
from core.base import format_file_path, format_name
from core.constants import DISABLE_TRACKING, IGNORE_TRACKING
from core.os import list_directory, load_executable, mouse_press, mouse_move, key_press, get_running_processes


COMMANDS_PATH = format_file_path('%DOCUMENTS%/Mouse Tracks/Commands')

COMMANDS_FILES = list_directory(COMMANDS_PATH, remove_extensions=True, force_extension='ini')


def running_applications_with_commands(profile_names=COMMANDS_FILES):
    """Get list of currently running apps that have associated commands."""
    result = set()
    all_applications = [format_name(i) for i in get_running_processes().keys()]
    for profile_name in RunningApplications().all_loaded_apps():
        if profile_name in (DISABLE_TRACKING, IGNORE_TRACKING):
            continue
        result.add(profile_name)
    return result