"""Entry point for MouseTracks 2."""

import os
import sys
from contextlib import suppress
from multiprocessing import freeze_support

# Source DLL files when running as an executable
from mousetracks2.constants import REPO_DIR
sys.path.append(str(REPO_DIR / 'resources' / 'build'))

from mousetracks2.components import Hub
from mousetracks2.constants import REPO_DIR
from mousetracks2.config.cli import CLI, parse_args
from mousetracks2.utils.system import is_elevated, relaunch_as_elevated, check_autostart


if __name__ == '__main__':
    freeze_support()

    # Update startup path if if running a built executable
    with suppress(NotImplementedError):
        check_autostart()

    # Check there aren't any invalid arguments
    # This is the only place where this check is safe to do
    parse_args(strict=True)

    # Relaunch as elevated
    if CLI.elevate and not is_elevated():
        relaunch_as_elevated()

    Hub(use_gui=True).run()
