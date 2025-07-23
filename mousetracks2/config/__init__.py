from .cli import CLI
from .settings import GlobalConfig, ProfileConfig


def should_minimise_on_start() -> bool:
    """Determine if the app should minimise on startup."""
    return CLI.start_hidden or CLI.autostart and GlobalConfig().minimise_on_start
