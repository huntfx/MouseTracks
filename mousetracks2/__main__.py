"""Entry point for MouseTracks 2."""

import os
import sys
from contextlib import suppress
from multiprocessing import freeze_support

try:
    import filelock

    # Source DLL files when running as an executable
    from mousetracks2.runtime import DATA_DIR, REPO_DIR, IS_BUILT_EXE
    sys.path.append(str(REPO_DIR / 'resources' / 'build'))

    # Set per-monitor DPI aware
    from mousetracks2.utils.system import force_physical_dpi_awareness
    force_physical_dpi_awareness()

    from mousetracks2.components import Hub
    from mousetracks2.config import GlobalConfig
    from mousetracks2.cli import CLI, parse_args, run_cli_function
    from mousetracks2.utils.system import is_elevated, relaunch_as_elevated, remap_autostart
    from mousetracks2.utils.update import background_update
    from mousetracks2.utils.system import update_installer_version_number

# Show any errors as the app otherwise will just silently fail
except Exception:
    import traceback
    traceback.print_exc()
    input('Press enter to exit...')
    sys.exit(1)


def main() -> None:
    """Handle the main startup checks and logic."""
    # Set the installer version number to the currently running version
    if CLI.installed:
        update_installer_version_number()

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
        background_update(download=not CLI.offline)

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

    # Check for specific CLI args
    if not run_cli_function():

        # Launch the application
        try:
            with filelock.FileLock(DATA_DIR / '.lock', timeout=0):
                main()

        # Notify the user if another instance is running
        except filelock.Timeout:
            print(f'Error: Another instance of MouseTracks is already writing to "{DATA_DIR}".')
            input('Press enter to exit...')
