import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, IO

import yaml

from .cli import CLI
from .utils import keycodes


GLOBAL_CONFIG_PATH = CLI.data_dir / 'config.yaml'


@dataclass
class GlobalConfig:
    """Settings to save to disk.

    Attributes:
        minimise_on_start: Minimise the application on startup.
        track_mouse: Enable mouse tracking.
        track_keyboard: Enable keyboard tracking.
        track_gamepad: Enable gamepad tracking.
        track_network: Enable network tracking.
        inactivity_time: How long before the user is classed as inactive.
        save_frequency: How often to autosave.
        max_loaded_profiles: Maximum amount of loaded profiles.
            This will only affect profiles without unsaved changes.
        gamepad_check_frequency: How often to check the connected gamepads.
        application_check_frequency: How often to check the current focused application.
        component_check_frequency: How often to check all components are running.
            This is used once per message received.
        shutdown_timeout: How long to wait before shutting down automatically.
            This is to avoid blocking Windows from shutting down.
            The default `HungAppTimeout` is 5 seconds and `WaitToKillAppTimeout` is
            20 seconds, so don't exceed 25 seconds or it may get terminated.
        export_notification_timeout: How long to show the export notification for.
        preview_frequency_multiplier: How often to re-render the preview image.
    """

    minimise_on_start: bool = False
    track_mouse: bool = True
    track_keyboard: bool = True
    track_gamepad: bool = True
    track_network: bool = True
    inactivity_time: float = 300.0
    save_frequency: float = 600.0
    max_loaded_profiles: int = 8
    gamepad_check_frequency: float = 1.0
    application_check_frequency: float = 1.0
    component_check_frequency: float = 1.0
    shutdown_timeout: float = 15.0
    export_notification_timeout: float = 7.0
    preview_frequency_multiplier: float = 1.0

    def __post_init__(self) -> None:
        self.load()

    def save(self, path: str | Path = GLOBAL_CONFIG_PATH) -> None:
        """Save the config to a YAML file."""
        # Ensure the folder exists
        base_dir = os.path.dirname(path)
        if not os.path.exists(base_dir):
            os.makedirs(base_dir)

        # Save the data
        with open(path, 'w', encoding='utf-8') as f:
            yaml.dump(self.__dict__, f, default_flow_style=False)

    def load(self, path: str | Path = GLOBAL_CONFIG_PATH) -> None:
        """Load the config from a YAML file, if it exists."""
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                self.__dict__.update(yaml.safe_load(f))

        # Create the config file if it doesn't exist
        else:
            self.save()


@dataclass
class ProfileConfig:
    """Settings to save to a profile."""

    multi_monitor: bool | None = None
    track_mouse: bool = True
    track_keyboard: bool = True
    track_gamepad: bool = True
    track_network: bool = True
    disabled_resolutions: list[tuple[int, int]] = field(default_factory=list)

    def save(self, f: IO[bytes]) -> None:
        """Save the config to a YAML file."""
        data = self.__dict__.copy()
        data['disabled_resolutions'] = [f'{w}x{h}' for w, h in self.disabled_resolutions]
        yaml.dump(data, f, default_flow_style=False, encoding='utf-8')

    def load(self, f: IO[bytes]) -> None:
        """Load the config from a YAML file if it exists."""
        data: dict[str, Any] = yaml.safe_load(f.read())
        resolutions: list[str] = data.pop('disabled_resolutions', [])
        self.__dict__.update(data)
        self.disabled_resolutions = []
        for res in resolutions:
            width, height = map(int, res.split('x'))
            self.disabled_resolutions.append((width, height))

    def should_track_keycode(self, keycode: int) -> bool:
        """Determine if a keycode should be tracked."""
        if keycode in keycodes.MOUSE_CODES or keycode in keycodes.SCROLL_CODES:
            return self.track_mouse
        if keycode in keycodes.KEYBOARD_CODES:
            return self.track_keyboard
        raise NotImplementedError(keycode)
