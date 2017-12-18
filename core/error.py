"""
This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""

from __future__ import absolute_import

import sys

from core.base import format_file_path
from core.compatibility import input, Message, PYTHON_VERSION
from core.constants import DEFAULT_PATH
from core.language import Language
from core.os import OPERATING_SYSTEM
from core.versions import VERSION, FILE_VERSION


def handle_error(trace=None, log=True):
    """Any errors are sent to here."""
    if trace is not None:
    
        output = ['Mouse Tracks {} ({}) | Python {} | {}'.format(VERSION, FILE_VERSION, PYTHON_VERSION, OPERATING_SYSTEM)]
        output.append('')
        output.append(trace)
        output = '\n'.join(output)
        
        if log:
            file_name = format_file_path('{}\\error.txt'.format(DEFAULT_PATH))
            with open(file_name, 'w') as f:
                f.write(output)
        Message(trace)
        
        string = Language().get_strings()
        input(string['string']['exit'])
    
    sys.exit(0)