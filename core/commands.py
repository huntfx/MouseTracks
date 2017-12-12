"""
This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""

from __future__ import absolute_import

import time
import os

from core.base import format_file_path, format_name
from core.os import list_directory, load_executable, mouse_press, mouse_move, key_press


COMMANDS_PATH = format_file_path('%DOCUMENTS%/Mouse Tracks/Commands')

COMMANDS_FILES = list_directory(COMMANDS_PATH, remove_extensions=True, force_extension='txt')


def read_commands(profile_name=None):

    profile_name = format_name(profile_name)
    
    if profile_name not in COMMANDS_FILES:
        return
    
    file_name = os.path.join(COMMANDS_PATH, '{}.txt'.format(profile_name))
    with open(file_name, 'r') as f:
        lines = [i.split('#', 1)[0].strip() for i in f.readlines()]
    
    #Iterate through each command
    for line in lines:
        parts = line.split('\t')
        
        #Skip invalid lines
        if len(parts) < 2:
            continue
        
        trigger = parts[0]
        command = parts[1]
        
        #Record list of commands
        if command in ('LAUNCH', 'FORCE_LAUNCH'):
            program = parts[2]
            
        elif command == 'MOUSECLICK':
            mouse_button = parts[2]
            
        elif command == 'MOUSEMOVE':
            mouse_pos_x = parts[2]
            mouse_pos_y = parts[3]
            
        elif command.startswith('KEYPRESS_'):
            key_code = parts[2]
            
        elif command == 'WAIT':
            wait_trigger = parts[2]
            seconds = parts[3]
                
    raise NotImplementedError