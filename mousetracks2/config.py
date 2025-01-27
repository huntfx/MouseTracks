from dataclasses import dataclass
from typing import BinaryIO

import yaml

from .constants import BASE_DIR


GLOBAL_CONFIG_PATH = BASE_DIR / 'config.yaml'


@dataclass
class GlobalConfig:
    """Settings to save to disk."""

    minimise_on_start: bool = False

    def __post_init__(self):
        self.load()

    def save(self):
        """Save the config to a YAML file."""
        with open(GLOBAL_CONFIG_PATH, "w", encoding="utf-8") as f:
            yaml.dump(self.__dict__, f, default_flow_style=False)

    def load(self):
        """Load the config from a YAML file, if it exists."""
        if GLOBAL_CONFIG_PATH.exists():
            with open(GLOBAL_CONFIG_PATH, 'r', encoding='utf-8') as f:
                self.__dict__.update(yaml.safe_load(f))

        # Create the config file if it doesn't exist
        else:
            self.save()


@dataclass
class ProfileConfig:
    """Settings to save to a profile."""

    def save(self, f: BinaryIO) -> None:
        """Save the config to a YAML file."""
        yaml.dump(self.__dict__, f, default_flow_style=False, encoding='utf-8')

    def load(self, f: BinaryIO):
        """Load the config from a YAML file if it exists."""
        self.__dict__.update(yaml.safe_load(f.read()))
