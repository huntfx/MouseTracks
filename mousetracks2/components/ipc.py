"""Standard format for data to be sent through communication queues."""

from dataclasses import dataclass, field
from enum import Enum, auto
import numpy as np

from ..config import ProfileConfig


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
    Speed = auto()
    SingleClick = auto()
    DoubleClick = auto()
    HeldClick = auto()
    Thumbstick_Time = auto()
    Thumbstick_Speed = auto()
    Thumbstick_Heatmap = auto()
    Keyboard = auto()


class TrackingState(Enum):
    """Current state of the application.

    If paused, then the components are still running and just skip
    executing certain commands. Messages may still be sent.
    If stopped, then all processes have been fully shut down, and
    can only be restarted by the hub.
    """

    Running = auto()
    Paused = auto()
    Stopped = auto()


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
    keycode: int


@dataclass
class KeyHeld(Message):
    """Key is being held.
    This does not trigger on the first press.
    """

    target: int = field(default=Target.Processing | Target.GUI, init=False)
    keycode: int


@dataclass
class ButtonPress(Message):
    """Gamepad button has been pressed."""

    target: int = field(default=Target.Processing | Target.GUI, init=False)
    gamepad: int
    keycode: int


@dataclass
class ButtonHeld(Message):
    """Gamepad button is being held."""

    target: int = field(default=Target.Processing, init=False)
    gamepad: int
    keycode: int


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
class StartTracking(Message):
    """Send a request to start tracking.
    Once this is processed, the `TrackingStarted` message will be sent.
    """
    target: int = field(default=Target.Tracking | Target.Hub, init=False)


@dataclass
class TrackingStarted(Message):
    """Send a message after tracking has started."""
    target: int = field(default=Target.Processing | Target.GUI, init=False)


@dataclass
class PauseTracking(Message):
    """Send a request to pause tracking."""
    target: int = field(default=Target.Hub | Target.Tracking | Target.GUI, init=False)


@dataclass
class StopTracking(Message):
    """Send a request to stop tracking."""
    target: int = field(default=Target.Hub | Target.Tracking | Target.Processing | Target.AppDetection | Target.GUI, init=False)


@dataclass
class MonitorsChanged(Message):
    """Send the location of each monitor when the setup changes."""

    target: int = field(default=Target.GUI | Target.Processing, init=False)
    data: list[tuple[int, int, int, int]]


@dataclass
class RenderRequest(Message):
    """Request a render.

    If profile is None then the currently loaded profile will be
    rendered.
    """

    target: int = field(default=Target.Processing, init=False)
    type: RenderType
    width: int | None
    height: int | None
    colour_map: str
    sampling: int
    profile: str | None
    file_path: str | None
    padding: int = 0
    contrast: float = 1.0
    lock_aspect: bool = True


@dataclass
class Render(Message):
    """A render has been completed."""

    target: int = field(default=Target.GUI, init=False)
    array: np.ndarray
    request: RenderRequest



@dataclass
class RequestRunningAppCheck(Message):
    """Check which applications are running."""

    target: int = field(default=Target.AppDetection, init=False)


@dataclass
class TrackedApplicationDetected(Message):
    """Trigger a profile change.
    This is sent from the application detection thread.
    """

    target: int = field(default=Target.Processing | Target.Tracking | Target.GUI, init=False)
    name: str
    process_id: int | None
    rect: tuple[int, int, int, int] | None


@dataclass
class ApplicationFocusChanged(Message):
    """Send a notification whenever a new application is focused.
    This is for debugging and is not used for logic.
    """

    target: int = field(default=Target.GUI, init=False)
    exe: str
    title: str
    tracked: bool



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
class ProfileDataRequest(Message):
    target: int = field(default=Target.Processing, init=False)
    profile_name: str | None = field(default=None)


@dataclass
class ProfileData(Message):
    """Information about a profile."""

    target: int = field(default=Target.GUI, init=False)
    profile_name: str
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
    config: ProfileConfig


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


@dataclass
class SetProfileMouseTracking(Message):
    target: int = field(default=Target.Processing, init=False)
    profile_name: str
    enable: bool


@dataclass
class SetProfileKeyboardTracking(Message):
    target: int = field(default=Target.Processing, init=False)
    profile_name: str
    enable: bool


@dataclass
class SetProfileGamepadTracking(Message):
    target: int = field(default=Target.Processing, init=False)
    profile_name: str
    enable: bool


@dataclass
class SetProfileNetworkTracking(Message):
    target: int = field(default=Target.Processing, init=False)
    profile_name: str
    enable: bool


@dataclass
class SetGlobalMouseTracking(Message):
    target: int = field(default=Target.Tracking, init=False)
    enable: bool


@dataclass
class SetGlobalKeyboardTracking(Message):
    target: int = field(default=Target.Tracking, init=False)
    enable: bool


@dataclass
class SetGlobalGamepadTracking(Message):
    target: int = field(default=Target.Tracking, init=False)
    enable: bool


@dataclass
class SetGlobalNetworkTracking(Message):
    target: int = field(default=Target.Tracking, init=False)
    enable: bool


@dataclass
class DeleteMouseData(Message):
    target: int = field(default=Target.Processing, init=False)
    profile_name: str


@dataclass
class DeleteKeyboardData(Message):
    target: int = field(default=Target.Processing, init=False)
    profile_name: str


@dataclass
class DeleteGamepadData(Message):
    target: int = field(default=Target.Processing, init=False)
    profile_name: str


@dataclass
class DeleteNetworkData(Message):
    target: int = field(default=Target.Processing, init=False)
    profile_name: str


@dataclass
class Autosave(Message):
    target: int = field(default=Target.Tracking, init=False)
    enabled: bool


@dataclass
class RequestQueueSize(Message):
    target: int = field(default=Target.Hub, init=False)


@dataclass
class QueueSize(Message):
    target: int = field(default=Target.GUI, init=False)
    hub: int
    tracking: int
    processing: int
    gui: int
    app_detection: int


@dataclass
class ToggleConsole(Message):
    target: int = field(default=Target.Hub, init=False)
    show: bool


@dataclass
class InvalidConsole(Message):
    target: int = field(default=Target.GUI, init=False)


@dataclass
class CloseSplashScreen(Message):
    """Send a request to close the splash screen.
    The splash screen is run by the hub, and waits for the GUI to finish
    loading before closing.
    """

    target: int = field(default=Target.Hub, init=False)


@dataclass
class LoadLegacyProfile(Message):
    """Send a request to load an old profile."""

    target: int = field(default=Target.Processing | Target.GUI, init=False)

    name: str
    path: str
