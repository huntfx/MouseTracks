"""Entry point for MouseTracks 2."""

import os
import sys
from contextlib import suppress
from multiprocessing import freeze_support
from threading import Thread

import filelock

# Source DLL files when running as an executable
from mousetracks2.constants import REPO_DIR, APP_EXECUTABLE
sys.path.append(str(REPO_DIR / 'resources' / 'build'))

from mousetracks2.components import Hub
from mousetracks2.constants import REPO_DIR, IS_BUILT_EXE
from mousetracks2.config import GlobalConfig
from mousetracks2.cli import CLI, parse_args
from mousetracks2.utils.system import is_elevated, relaunch_as_elevated, get_autostart, remap_autostart
from mousetracks2.utils.update import cleanup_old_executables, download_version


def _installer_update() -> None:
    """Handle downloads/cleanup if running as an installed application."""
    app_dir = APP_EXECUTABLE.parent
    cleanup_old_executables(app_dir)
    if not CLI.offline:
        download_version(app_dir)


def main() -> None:
    """Handle the main startup checks and logic."""
    # Update config if start hidden/visible command line argument is set
    if CLI.start_hidden is not None:
        config = GlobalConfig()
        config.minimise_on_start = CLI.start_hidden
        config.save()

    # Update autostart path if necessary
    with suppress(NotImplementedError):
        remap_autostart()

    # Trigger the updater
    if CLI.installed:
        Thread(target=_installer_update).start()

    # Run the main application
    Hub(use_gui=True).run()


if __name__ == '__main__':
    freeze_support()

    # Add certs
    if IS_BUILT_EXE:
        cert_path = REPO_DIR / 'certifi' / 'cacert.pem'
        os.environ['SSL_CERT_FILE'] = str(cert_path)

    # Check there aren't any invalid arguments
    # This is the only place where this check is safe to do
    parse_args(strict=True)

    # Relaunch as elevated
    if CLI.elevate and not is_elevated():
        relaunch_as_elevated()

    # Launch the application
    try:
        with filelock.FileLock(CLI.data_dir / '.lock', timeout=0):
            main()

    # Notify the user if another instance is running
    except filelock.Timeout:
        print(f'Error: Another instance of MouseTracks is already writing to "{CLI.data_dir}".')
        input('Press enter to exit...')
