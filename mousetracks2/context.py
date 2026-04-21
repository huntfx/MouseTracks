from contextlib import suppress
from pathlib import Path
from typing import Sequence

import psutil

from .cli import CLI
from .runtime import APPDATA, CURRENT_DIR, SYS_EXECUTABLE, IS_BUILT_EXE, REPO_DIR


class Context:
    """Dynamically resolved global variables."""

    def __init__(self, args: Sequence[str] | None = None) -> None:
        self.cli = CLI(args)

        self._data_dir: Path | None = None
        self._launch_executable: Path | None = None
        self._executable_dir: Path | None = None

    @property
    def launch_executable(self) -> Path:
        """The executable that was used to launch MouseTracks."""
        if self._launch_executable is None:
            if self.cli.installed:
                # Fallback to expected path
                self._launch_executable = SYS_EXECUTABLE.parent / 'MouseTracks.exe'

                # Attempt to get the correct path
                with suppress(psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    current_proc = psutil.Process()
                    current_exe = current_proc.exe()
                    for parent in current_proc.parents():
                        parent_exe = parent.exe()
                        if parent_exe != current_exe:
                            self._launch_executable = Path(parent_exe)
                            break
            else:
                self._launch_executable = SYS_EXECUTABLE
        return self._launch_executable

    @property
    def executable_dir(self) -> Path:
        """The location of all other executables."""
        if self._executable_dir is None:
            if IS_BUILT_EXE:
                self._executable_dir = self.launch_executable.parent
            else:
                self._executable_dir = REPO_DIR
        return self._executable_dir

    @property
    def offline(self) -> bool:
        """Force offline mode so that no connections are ever made."""
        return self.cli.offline

    @property
    def start_hidden(self) -> bool | None:
        """Start the application as hidden."""
        return self.cli.start_hidden

    @property
    def autostart(self) -> bool:
        """Flag when automatically launched at startup."""
        return self.cli.autostart

    @property
    def data_dir(self) -> Path:
        """Get the data directory path."""
        if self._data_dir is None:
            if self.cli.data_dir is None:
                if self.cli.portable:
                    self._data_dir = CURRENT_DIR / '.mousetracks'
                else:
                    self._data_dir = APPDATA / 'MouseTracks'
            else:
                self._data_dir = self.cli.data_dir
        return self._data_dir

    @property
    def disable_splash(self) -> bool:
        """Disable the splash screen."""
        return self.cli.disable_splash

    @property
    def disable_mouse(self) -> bool:
        """Disable mouse tracking."""
        return self.cli.disable_mouse

    @property
    def disable_keyboard(self) -> bool:
        """Disable keyboard tracking."""
        return self.cli.disable_keyboard

    @property
    def disable_gamepad(self) -> bool:
        """Disable gamepad tracking."""
        return self.cli.disable_gamepad

    @property
    def disable_network(self) -> bool:
        """Disable network tracking."""
        return self.cli.disable_network

    @property
    def elevate(self) -> bool:
        """Run with elevated privileges."""
        return self.cli.elevate

    @property
    def portable(self) -> bool:
        """If running as a portable application."""
        return self.cli.portable

    @property
    def single_monitor(self) -> bool:
        """Treat all monitors as a single monitor."""
        return self.cli.single_monitor

    @property
    def multi_monitor(self) -> bool:
        """Handle each monitor separately."""
        return self.cli.multi_monitor

    @property
    def installed(self) -> bool:
        """Determine if running installed or portable."""
        return self.cli.installed

    @property
    def post_install(self) -> bool:
        """Determine if running straight after being installed."""
        return self.cli.post_install


CTX = Context()
