"""Entry point for Mousetracks 2, without error handling.

Usage: `python -m mousetracks2`
"""

from contextlib import suppress
from multiprocessing import freeze_support

import filelock

from .components import Hub
from .config import GlobalConfig
from .context import CTX
from .cli import parse_args, run_cli_function
from .popups import show_temp_warning_dialog, show_already_running_dialog
from .utils.system import is_elevated, relaunch_as_elevated, remap_autostart
from .utils.update import background_update
from .utils.system import update_installer_version_number


def run() -> None:
    """Run the application."""
    # Warn if saving to temp dir
    print(f'Application data location: {CTX.data_dir}')
    if CTX.saving_to_temp and not show_temp_warning_dialog():
        return

    # Set the installer version number to the currently running version
    if CTX.installed:
        update_installer_version_number()
        background_update(download=not CTX.offline)

    # Update config if start hidden/visible command line argument is set
    if CTX.start_hidden is not None:
        config = GlobalConfig()
        config.minimise_on_start = CTX.start_hidden
        config.save()

    # Update autostart path if necessary
    with suppress(NotImplementedError):
        remap_autostart()

    # Run the main application
    Hub(use_gui=True).run()


def main() -> None:
    """Run the application after checks are done."""
    # Check there aren't any invalid arguments
    # This is the only place where this check is safe to do
    parse_args(strict=True)

    # Relaunch as elevated
    if CTX.elevate and not is_elevated():
        relaunch_as_elevated()

    # Check for specific CLI args
    if not run_cli_function(CTX.cli):

        # Launch the application
        try:
            with filelock.FileLock(CTX.data_dir / '.lock', timeout=0):
                run()

        # Notify the user if another instance is running
        except filelock.Timeout:
            show_already_running_dialog(CTX.data_dir)


if __name__ == '__main__':
    freeze_support()
    main()
