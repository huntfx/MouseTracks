"""Standard format for data to be sent through communication queues."""

from dataclasses import dataclass, field
from enum import Enum, IntFlag, auto
from typing import Literal

import numpy as np
import numpy.typing as npt

from ..config import ProfileConfig
from ..enums import BlendMode, Channel
from ..types import RectList
from ..utils.monitor import MonitorData


class Target:
    """System components that can send or receive messages."""

    Hub = 2 ** 0
    Tracking = 2 ** 1
    Processing = 2 ** 2
    GUI = 2 ** 3
    AppDetection = 2 ** 4


class RenderType(Enum):
    """Possible types of renders."""

    MouseMovement = auto()
    MouseSpeed = auto()
    MousePosition = auto()
    SingleClick = auto()
    DoubleClick = auto()
    HeldClick = auto()
    ThumbstickMovement = auto()
    ThumbstickSpeed = auto()
    ThumbstickPosition = auto()
    KeyboardHeatmap = auto()


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

    def reraise(self) -> None:
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
    data: MonitorData


@dataclass
class RenderRequest(Message):
    """Request a render.

    If profile is None then the currently loaded profile will be
    rendered.
    """

    target: int = field(default=Target.Processing, init=False)
    type: RenderType
    profile: str | None
    file_path: str | None
    width: int | None
    height: int | None
    colour_map: str
    linear: bool
    sampling: int = 1
    padding: int = 0
    contrast: float = 1.0
    lock_aspect: bool = True
    clipping: float = 1.0
    blur: float = 0.0
    invert: bool = False
    show_left_clicks: bool = True
    show_middle_clicks: bool = True
    show_right_clicks: bool = True
    show_count: bool = True
    show_time: bool = False
    interpolation_order: Literal[0, 1, 2, 3, 4, 5] = 0
    layer_visible: bool = True

    def __post_init__(self) -> None:
        assert self.show_count != self.show_time


@dataclass
class Render(Message):
    """A render has been completed."""

    target: int = field(default=Target.GUI, init=False)
    array: npt.NDArray[np.uint8]
    request: RenderRequest



@dataclass
class RequestRunningAppCheck(Message):
    """Check which applications are running."""

    target: int = field(default=Target.AppDetection, init=False)


@dataclass
class TrackedApplicationDetected(Message):
    """Detect when a new tracked application is focused.

    This was originally processed by all components, but there was a
    rare chance of a race condition where the active time was 1 tick
    higher than the elapsed time. Now it notifies just the tracking
    component, which then it turn sends a separate message out to the
    other components, but in sync with the ticks.
    """

    target: int = field(default=Target.Tracking, init=False)
    name: str
    process_id: int | None
    rects: RectList = field(default_factory=RectList)


@dataclass
class CurrentProfileChanged(Message):
    """Trigger a profile switch.

    This is a variation of `TrackedApplicationDetected`, but is in
    sync with the tick counter to prevent race conditions.
    """

    target: int = field(default=Target.Processing | Target.GUI, init=False)
    name: str
    process_id: int | None
    rects: RectList = field(default_factory=RectList)


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

    target: int = field(default=Target.Hub | Target.Tracking | Target.Processing | Target.AppDetection | Target.GUI, init=False)


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
    profile_name: str | None = None


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
    sanitised_name: str
    profile_name: str


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
    resolutions: dict[tuple[int, int], tuple[int, bool]]
    multi_monitor: bool | None


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
class DebugDisableAppDetection(Message):
    target: int = field(default=Target.Tracking, init=False)
    disable: bool


@dataclass
class DebugDisableMonitorCheck(Message):
    target: int = field(default=Target.Tracking, init=False)
    disable: bool


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
class DeleteProfile(Message):
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
    """Change the visible state of the console."""
    target: int = field(default=Target.Hub | Target.GUI, init=False)
    show: bool


@dataclass
class InvalidConsole(Message):
    """Triggered if the console is determined to be not valid.
    This may be the built in console in an IDE for example.
    """
    target: int = field(default=Target.GUI, init=False)


@dataclass
class CloseSplashScreen(Message):
    """Send a request to close the splash screen.
    The splash screen is run by the hub, and waits for the GUI to finish
    loading before closing.
    """

    target: int = field(default=Target.Hub | Target.GUI, init=False)


@dataclass
class ImportProfile(Message):
    """Send a request to import a profile."""

    target: int = field(default=Target.Processing | Target.GUI, init=False)
    name: str
    path: str


@dataclass
class ImportLegacyProfile(Message):
    """Send a request to import a legacy profile."""

    target: int = field(default=Target.Processing | Target.GUI, init=False)
    name: str
    path: str


@dataclass
class FailedProfileImport(Message):
    """Send a request to import a legacy profile."""

    target: int = field(default=Target.GUI, init=False)
    source: ImportProfile | ImportLegacyProfile


@dataclass
class ExportStats(Message):
    target: int = field(default=Target.Processing, init=False)
    profile: str
    path: str


@dataclass
class ExportMouseStats(ExportStats):
    """Export the mouse statistics."""


@dataclass
class ExportKeyboardStats(ExportStats):
    """Export the keyboard statistics."""


@dataclass
class ExportGamepadStats(ExportStats):
    """Export the gamepad statistics."""


@dataclass
class ExportNetworkStats(ExportStats):
    """Export the network statistics."""


@dataclass
class ExportDailyStats(ExportStats):
    """Export the daily statistics."""


@dataclass
class ExportStatsSuccessful(Message):
    """Send a message when the export was successful."""

    target: int = field(default=Target.GUI, init=False)
    source: ExportStats


@dataclass
class ReloadAppList(Message):
    """Reload AppList.txt."""

    target: int = field(default=Target.AppDetection | Target.GUI, init=False)


@dataclass
class ToggleProfileResolution(Message):
    """Enable or disable a resolution for a profile."""

    target: int = field(default=Target.Processing, init=False)
    profile: str
    resolution: tuple[int, int]
    enable: bool


@dataclass
class ToggleProfileMultiMonitor(Message):
    """Change multi monitor handling for a profile."""

    target: int = field(default=Target.Processing, init=False)
    profile: str
    multi_monitor: bool | None


@dataclass
class RequestPID(Message):
    """Request a components PID."""


@dataclass
class SendPID(Message):
    """Send a components PID."""

    target: int = field(default=Target.GUI, init=False)
    source: int
    pid: int


@dataclass
class RenderLayer:
    """Hold a render request with layer data."""
    request: RenderRequest
    blend_mode: BlendMode
    channels: Channel = Channel.RGBA
    opacity: int = 100


@dataclass
class RenderLayerRequest(Message):
    """Request a render of multiple layers.

    Note that this is only meant to be a wrapper over the rendering, so
    for example this is why the resolution is stored per render request,
    rather than once per render layer request.
    """

    target: int = field(default=Target.Processing, init=False)
    layers: list[RenderLayer]


@dataclass
class ComponentLoaded(Message):
    """Notify when a single component has loaded."""

    target: int = field(default=Target.Hub, init=False)
    component: int


@dataclass
class AllComponentsLoaded(Message):
    """Notify once every component has been loaded."""

    target: int = field(default=Target.Hub | Target.GUI, init=False)


@dataclass
class ShowPopup(Message):
    """Trigger a popup message in the GUI."""

    target: int = field(default=Target.GUI, init=False)
    content: str
