"""
This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""

from __future__ import absolute_import

import os
import sys

from core.os._load_from_os import *


ARGUMENT_ELEVATE = 'Elevate'

ARGUMENT_IMAGEGEN = 'GenerateImage'


def _launch(add_arguments=[], remove_arguments=[], visible=True):
    """Launch a new instance of python with arguments provided."""
    if isinstance(add_arguments, str):
        add_arguments = [add_arguments]
    if isinstance(remove_arguments, str):
        remove_arguments = [remove_arguments]
        
    script = os.path.abspath(sys.argv[0])
    params = ' '.join([script] + [i for i in sys.argv[1:] if i not in remove_arguments] + list(add_arguments))
    return launch_console(params=params, visible=visible)

    
def should_generate_image():
    return ARGUMENT_IMAGEGEN in sys.argv

    
def has_been_elevated():
    return ARGUMENT_ELEVATE in sys.argv
    

def elevate(visible=True):
    """Attempt to elevate the current script and quit the original if successful."""
    if is_elevated() or ARGUMENT_ELEVATE in sys.argv:
        return True
    
    if _launch(visible=visible, add_arguments=[ARGUMENT_ELEVATE]):
        sys.exit(0)
    
    return False


def generate_images():
    """Launch new window to generate images.
    Removes elevation as it's not needed, and we don't want UAC to fire again.
    """
    _launch(visible=True, add_arguments=[ARGUMENT_IMAGEGEN], remove_arguments=[ARGUMENT_ELEVATE])