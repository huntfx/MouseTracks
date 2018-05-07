"""This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""

from __future__ import absolute_import, division

import time
import sys
import webbrowser
from multiprocessing import freeze_support

from core.image import user_generate


if __name__ == '__main__':
    freeze_support()
    user_generate()