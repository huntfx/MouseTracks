"""
This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""

from __future__ import absolute_import

from multiprocessing import freeze_support

from core.compatibility import PYTHON_VERSION
from core.constants import *
from core.config import CONFIG
from core.track import start_tracking
from core.os import elevate
if __name__ == '__main__':
    
    freeze_support()
    
    if CONFIG['Advanced']['RunAsAdministrator']:
        elevate()
    
    start_tracking()
