"""Standard format for data to be sent through communication queues."""

from dataclasses import dataclass, field
from enum import Enum, auto
import numpy as np


class Target:
    """System components that can send or receive messages."""

    Hub = 0b1
    Tracking = 0b10
    Processing = 0b100
    GUI = 0b1000


class ThumbnailType(Enum):
    """Possible types of thumbnail renders."""

    Time = auto()
    Speed = auto()


@dataclass
class Message:
    """Represents an item to be passed through a communication queue.

    Attributes:
        target: The intended recipient component of the message.
        type: The type of message being sent.
        data: Optional data payload associated with the message.
    """

    target: int = field(default=0)


@dataclass
class MouseMove(Message):
    """Mouse has moved to a new location on the screen."""

    target: int = field(default=Target.Processing | Target.GUI, init=False)
    tick: int
    position: tuple[int, int]


@dataclass
class MouseClick(Message):
    """Mouse has been clicked."""

    target: int = field(default=Target.GUI, init=False)
    button: int
    position: tuple[int, int]
    double: bool = field(default=False)


@dataclass
class Traceback(Message):
    """Send data when a traceback is raised."""

    target: int = field(default=Target.Hub, init=False)
    exception: Exception
    traceback: str

    def reraise(self):
        """Re-raise the exception.
        Since the full traceback isn't accessible from a different
        thread, replicate Python's behaviour by showing both exceptions.
        """
        print(self.traceback)
        print('During handling of the above exception, another exception occurred:\n')
        raise self.exception


@dataclass
class TrackingState(Message):
    """Set a tracking state."""

    class State(Enum):
        Start = auto()
        Pause = auto()
        Stop = auto()

    target: int = field(default=Target.Hub | Target.Tracking | Target.Processing, init=False)
    state: State


@dataclass
class MonitorsChanged(Message):
    """Send the location of each monitor when the setup changes."""

    target: int = field(default=Target.GUI | Target.Processing, init=False)
    data: list[tuple[int, int, int, int]]


@dataclass
class ThumbnailRequest(Message):
    """Request a thumbnail render."""

    target: int = field(default=Target.Processing, init=False)
    type: ThumbnailType
    width: int
    height: int


@dataclass
class Thumbnail(Message):
    """A thumbnail has been rendered."""
    target: int = field(default=Target.GUI, init=False)
    type: ThumbnailType
    data: np.ndarray
    tick: int


@dataclass
class Exit(Message):
    """Quit the whole application."""

    target: int = field(default=Target.Hub, init=False)


@dataclass
class DebugRaiseError(Message):
    """Raise an error for debugging."""


# Test code as an example to refer back to
if __name__ == '__main__':
    test = [
        MouseClick(button=1, position=(0, 0)),
        MouseClick(button=2, position=(0, 0)),
        MouseMove(position=(0, 0)),
    ]
    for data in test:
        match data:
            case MouseClick(button=1) if data.target & Target.GUI:
                print('Mouse button 1 clicked')
            case MouseClick():
                print(f'Mouse button {data.button} clicked at {data.position}')
            case MouseMove(position=pos):
                print(f'Mouse moved to {pos}')
            case _:
                print('Unknown item')
