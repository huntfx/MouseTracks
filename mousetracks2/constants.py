import os
import sys
from pathlib import Path

if hasattr(sys, '_MEIPASS'):
    REPO_DIR = Path(sys._MEIPASS)
else:
    REPO_DIR = Path(__file__).parent.parent

DEFAULT_PROFILE_NAME = 'Desktop'

UPDATES_PER_SECOND = 60

DOUBLE_CLICK_MS = 500
"""Maximum time in ms where a double click is valid."""

DOUBLE_CLICK_TOL = 8
"""Maximum pixels where a double click is valid."""

COMPRESSION_THRESHOLD = 425000  # Max: 2 ** 64 - 1
"""How many ticks to trigger track compression."""

COMPRESSION_FACTOR = 1.1
"""How much to compress tracks by."""

INACTIVITY_MS = 1000 * 60 * 5  # 5 mins
"""Time in ms before inactive."""

RADIAL_ARRAY_SIZE = 2048
"""Size to use for gamepad radial arrays."""

DEBUG = True
"""Switch on assertion statements for testing."""

IS_EXE = getattr(sys, 'frozen', False)
"""Determine if running as an executable."""

SHUTDOWN_TIMEOUT = 15.0
"""How many seconds to wait before shutting down automatically.
This is to avoid blocking Windows from shutting down.
The default `HungAppTimeout` is 5 seconds and `WaitToKillAppTimeout` is
20 seconds, so don't exceed 25 seconds or it may get terminated.
"""

CHECK_COMPONENT_FREQUENCY = 1.0
"""How often in seconds to check if all components are running."""

TRACKING_DISABLE = 'Untracked'
"""Turn off tracking for any applications with this name."""

TRACKING_IGNORE = '<ignore>'
"""Ignore tracking for any applications with this name.
This may be used when specifically excluding a splash screen.
"""

TRACKING_WILDCARD = '<*>'
