DEFAULT_PROFILE_NAME = 'Main'

UPDATES_PER_SECOND = 60

DOUBLE_CLICK_MS = 500
"""Maximum time in ms where a double click is valid."""

DOUBLE_CLICK_TOL = 8
"""Maximum pixels where a double click is valid."""

COMPRESSION_THRESHOLD = 425000  # Max: 2 ** 64 - 1
"""How many ticks to trigger track compression."""

COMPRESSION_FACTOR = 1.1
"""How much to compress tracks by."""

INACTIVITY_MS = 300000
"""Time in ms before inactive."""

RADIAL_ARRAY_SIZE = 2048
"""Size to use for gamepad radial arrays."""
