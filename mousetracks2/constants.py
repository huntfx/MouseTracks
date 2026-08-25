DEFAULT_PROFILE_NAME = 'Desktop'

UPDATES_PER_SECOND = 60

DOUBLE_CLICK_MS = 500
"""Maximum time in ms where a double click is valid."""

DOUBLE_CLICK_TOL = 8
"""Maximum pixels where a double click is valid."""

DECAY_THRESHOLD = 425000  # Max: 2 ** 64 - 1
"""How many ticks to trigger array value decay."""

DECAY_FACTOR = 1.1
"""How much to decay the arrays by."""

RADIAL_ARRAY_SIZE = 2048
"""Size to use for gamepad radial arrays."""

DEBUG = True
"""Switch on assertion statements for testing."""

TRACKING_DISABLE = 'Untracked'
"""Turn off tracking for any applications with this name."""

TRACKING_IGNORE = '<ignore>'
"""Ignore tracking for any applications with this name.
This may be used when specifically excluding a splash screen.
"""

TRACKING_WILDCARD = '<*>'

PACKAGE_IDENTIFIER = 'uk.peterhunt.mousetracks'

UNTRUSTED_EXT = '.skipped'

APP_BORDER_TOLERANCE = 32
