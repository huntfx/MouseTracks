"""Placeholder functions that do nothing.
These are used when code hasn't yet been written for an OS.
"""

def get_autostart(name: str) -> bool:
    """Determine if running on startup."""
    return False


def set_autostart(name: str, executable: str, *args: str) -> None:
    """Set to run on startup."""


def remove_autostart(name: str) -> None:
    """Stop running on startup."""


def is_elevated() -> bool:
    """Check if the script is running with admin privileges."""
    return False


def relaunch_as_elevated() -> None:
    """Relaunch the script with admin privileges."""
