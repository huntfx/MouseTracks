"""Standard format for data to be sent through communication queues."""

from dataclasses import dataclass, field
from enum import Enum, auto
import numpy as np


class Target:
    """System components that can send or receive messages."""

    Hub = 2 ** 0
    Tracking = 2 ** 1
    Processing = 2 ** 2
    GUI = 2 ** 3
    AppDetection = 2 ** 4


class RenderType(Enum):
    """Possible types of renders."""

    Time = auto()
    TimeHeatmap = auto()
    TimeSincePause = auto()
    Speed = auto()
    SingleClick = auto()
    DoubleClick = auto()
    HeldClick = auto()
    Thumbstick_R = auto()
    Thumbstick_L = auto()
    Thumbstick_C = auto()
    Thumbstick_R_SPEED = auto()
    Thumbstick_L_SPEED = auto()
    Thumbstick_C_SPEED = auto()
    Thumbstick_R_Heatmap = auto()
    Thumbstick_L_Heatmap = auto()
    Thumbstick_C_Heatmap = auto()


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
class Tick(Message):
    """Send the current tick."""

    target: int = field(default=Target.Processing | Target.GUI, init=False)
    tick: int
    timestamp: int


@dataclass
class MouseMove(Message):
    """Mouse has moved to a new location on the screen."""

    target: int = field(default=Target.Processing | Target.GUI, init=False)
    position: tuple[int, int]


@dataclass
class MouseClick(Message):
    """Mouse has been clicked."""

    target: int = field(default=Target.Processing | Target.GUI, init=False)
    button: int
    position: tuple[int, int]


@dataclass
class MouseHeld(Message):
    """Mouse button is being held."""

    target: int = field(default=Target.Processing | Target.GUI, init=False)
    button: int
    position: tuple[int, int]


@dataclass
class KeyPress(Message):
    """Key has been pressed."""

    target: int = field(default=Target.Processing | Target.GUI, init=False)
    opcode: int


@dataclass
class KeyHeld(Message):
    """Key is being held.
    This does not trigger on the first press.
    """

    target: int = field(default=Target.Processing | Target.GUI, init=False)
    opcode: int


@dataclass
class ButtonPress(Message):
    """Gamepad button has been pressed."""

    target: int = field(default=Target.Processing | Target.GUI, init=False)
    gamepad: int
    opcode: int


@dataclass
class ButtonHeld(Message):
    """Gamepad button is being held."""

    target: int = field(default=Target.Processing, init=False)
    gamepad: int
    opcode: int


@dataclass
class ThumbstickMove(Message):
    """Thumbstic location."""

    class Thumbstick(Enum):
        Left = auto()
        Right = auto()

    target: int = field(default=Target.Processing | Target.GUI, init=False)
    gamepad: int
    thumbstick: Thumbstick
    position: tuple[float, float]


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

    target: int = field(default=Target.Hub | Target.Tracking | Target.Processing | Target.AppDetection | Target.GUI, init=False)
    state: State


@dataclass
class MonitorsChanged(Message):
    """Send the location of each monitor when the setup changes."""

    target: int = field(default=Target.GUI | Target.Processing, init=False)
    data: list[tuple[int, int, int, int]]


@dataclass
class RenderRequest(Message):
    """Request a render."""

    target: int = field(default=Target.Processing, init=False)
    type: RenderType
    width: int | None
    height: int | None
    colour_map: str
    sampling: int
    application: str | None
    thumbnail: bool = field(default=False)


@dataclass
class Render(Message):
    """A render has been completed."""

    target: int = field(default=Target.GUI, init=False)
    array: np.ndarray
    sampling: int
    thumbnail: bool = field(default=False)



@dataclass
class RequestRunningAppCheck(Message):
    """Check which applications are running."""

    target: int = field(default=Target.AppDetection, init=False)


@dataclass
class ApplicationDetected(Message):
    """Update data about an application."""

    target: int = field(default=Target.Processing | Target.Tracking | Target.GUI, init=False)
    name: str
    process_id: int
    rect: tuple[int, int, int, int] | None


@dataclass
class Exit(Message):
    """Quit the whole application."""

    target: int = field(default=Target.Hub, init=False)


@dataclass
class DebugRaiseError(Message):
    """Raise an error for debugging."""


@dataclass
class ProcessShutDownNotification(Message):
    """Send a notification from a process that it has ended."""
    target: int = field(default=Target.Hub, init=False)
    source: int


@dataclass
class Save(Message):
    """Once a save is ready to be done."""

    target: int = field(default=Target.Processing, init=False)


@dataclass
class SaveComplete(Message):
    """After a profile has been saved."""

    target: int = field(default=Target.GUI, init=False)
    succeeded: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)


@dataclass
class Load(Message):
    target: int = field(default=Target.Processing, init=False)
    application: str | None = field(default=None)


@dataclass
class ProfileLoaded(Message):
    """Data containing information about the loaded profile."""

    target: int = field(default=Target.GUI, init=False)
    application: str | None
    distance: float
    cursor_counter: int
    thumb_l_counter: int
    thumb_r_counter: int
    clicks: int
    scrolls: int
    keys_pressed: int
    buttons_pressed: int
    elapsed_ticks: int
    active_ticks: int
    inactive_ticks: int
    bytes_sent: int
    bytes_recv: int


@dataclass
class DataTransfer(Message):
    """Upload and download data since the previous message."""

    target: int = field(default=Target.Processing | Target.GUI, init=False)
    mac_address: str
    bytes_sent: int
    bytes_recv: int


@dataclass
class Active(Message):

    target: int = field(default=Target.Processing | Target.GUI, init=False)
    profile_name: str
    ticks: int


@dataclass
class Inactive(Message):

    target: int = field(default=Target.Processing | Target.GUI, init=False)
    profile_name: str
    ticks: int

