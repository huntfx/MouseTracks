"""This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""
#Handle any errors that occur during execution
#At a future date it will send the error online

from __future__ import absolute_import

import sys

from .constants import DEFAULT_PATH
from .config.language import LANGUAGE
from .misc import TextFile, format_file_path
from .utils.compatibility import input, Message, PYTHON_VERSION
from .utils.os import OPERATING_SYSTEM
from .versions import VERSION, FILE_VERSION


def handle_error(trace=None, log=True, console=True):
    """Any errors are sent to here."""
    if trace is not None:
    
        #Generate output
        output = ['Mouse Tracks {} ({}) | Python {} | {}'.format(VERSION, FILE_VERSION, PYTHON_VERSION, OPERATING_SYSTEM)]
        output.append('')
        output.append(trace)
        output = '\n'.join(output)
        
        #Write to file
        if log:
            file_name = format_file_path('{}\\error.txt'.format(DEFAULT_PATH))
            with TextFile(file_name, 'w') as f:
                f.write(output)
        Message(trace.strip())
        
        #Output information to quit/restart
        #The try/except is in case the language code has failed
        try:
            error_message = LANGUAGE.strings['Misc']['ProgramError']
        except KeyError:
            error_message = 'An error occurred.'
        try:
            restart_message = LANGUAGE.strings['Misc']['ProgramRestart']
        except KeyError:
            restart_message = 'Please restart the program...'
        try:
            exit_message = LANGUAGE.strings['Misc']['ProgramExit']
        except KeyError:
            exit_message = 'Press enter to exit..'

        if console:
            input('{} {}'.format(error_message, exit_message))
        else:
            return Message('{} {}'.format(error_message, restart_message))
    sys.exit(0)
            