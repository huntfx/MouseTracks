"""Entry point for MouseTracks 2."""

import os
import sys
from contextlib import suppress
from multiprocessing import freeze_support

# Source DLL files when running as an executable
from mousetracks2.constants import REPO_DIR
sys.path.append(str(REPO_DIR / 'resources' / 'build'))

from mousetracks2.components import Hub
from mousetracks2.constants import REPO_DIR, IS_BUILT_EXE
from mousetracks2.config.cli import CLI, parse_args
from mousetracks2.utils.system import is_elevated, relaunch_as_elevated, get_autostart, remap_autostart


if __name__ == '__main__':
    freeze_support()

    # Add certs
    if IS_BUILT_EXE:
        cert_path = REPO_DIR / 'certifi' / 'cacert.pem'
        os.environ['SSL_CERT_FILE'] = str(cert_path)

    # Update startup path if running a built executable
    with suppress(NotImplementedError):
        cmd = get_autostart()
        if cmd is not None:
            remap_autostart(cmd)

    # Check there aren't any invalid arguments
    # This is the only place where this check is safe to do
    parse_args(strict=True)

    # Relaunch as elevated
    if CLI.elevate and not is_elevated():
        relaunch_as_elevated()

    Hub(use_gui=True).run()
