"""This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""
#Handle UTF-8 characters in the Python console, mainly for use with other languages
#Python 3 has the support built in by default

from __future__ import absolute_import

from ...utils.compatibility import PYTHON_VERSION
from ...utils.os import OPERATING_SYSTEM


if OPERATING_SYSTEM == 'Windows' and PYTHON_VERSION == 2:
    from . import win2