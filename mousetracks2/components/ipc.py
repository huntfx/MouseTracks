"""Standard format for data to be sent through communication queues."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, IntFlag, auto
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    import numpy as np
    import numpy.typing as npt

from ..config import ProfileConfig
from ..enums import BlendMode, Channel
from ..types import RectList
from ..utils.monitor import MonitorData


class Target(IntFlag):
    """System components that can send or receive messages."""

    Hub = auto()
    Tracking = auto()
    Processing = auto()
    GUI = auto()
    AppDetection = auto()
    Playback = auto()


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


class Device(IntFlag):
    """Input devices that can be tracked."""

    Mouse = auto()
    Keyboard = auto()
    Gamepad = auto()
    Network = auto()


@dataclass
class Message:
    """Represents an item to be passed through a communication queue.

    Attributes:
        target: The intended recipient component of the message.
        source: The component that sent the message.
    """

    target: Target = field(default=Target(0))
    source: Target = field(default_factory=lambda: Target(0), init=False)


@dataclass
class Tick(Message):
    """Send the current tick."""

    target: Target = field(default=Target.Hub | Target.Processing | Target.GUI | Target.Playback, init=False)
    tick: int
    timestamp: int


@dataclass
class MouseMove(Message):
    """Mouse has moved to a new location on the screen."""

    target: Target = field(default=Target.Processing | Target.GUI | Target.Playback, init=False)
    position: tuple[int, int]


@dataclass
class MouseClick(Message):
    """Mouse has been clicked."""

    target: Target = field(default=Target.Processing | Target.GUI | Target.Playback, init=False)
    button: int
    position: tuple[int, int]


@dataclass
class MouseHeld(Message):
    """Mouse button is being held."""

    target: Target = field(default=Target.Processing | Target.GUI | Target.Playback, init=False)
    button: int
    position: tuple[int, int]


@dataclass
class KeyPress(Message):
    """Key has been pressed."""

    target: Target = field(default=Target.Processing | Target.GUI | Target.Playback, init=False)
    keycode: int


@dataclass
class KeyHeld(Message):
    """Key is being held.
    This does not trigger on the first press.
    """

    target: Target = field(default=Target.Processing | Target.GUI | Target.Playback, init=False)
    keycode: int


@dataclass
class ButtonPress(Message):
    """Gamepad button has been pressed."""

    target: Target = field(default=Target.Processing | Target.GUI | Target.Playback, init=False)
    gamepad: int
    keycode: int


@dataclass
class ButtonHeld(Message):
    """Gamepad button is being held."""

    target: Target = field(default=Target.Processing | Target.Playback, init=False)
    gamepad: int
    keycode: int


@dataclass
class ThumbstickMove(Message):
    """Thumbstick location."""

    class Thumbstick(Enum):
        Left = auto()
        Right = auto()

    target: Target = field(default=Target.Processing | Target.GUI | Target.Playback, init=False)
    gamepad: int
    thumbstick: Thumbstick
    position: tuple[float, float]


@dataclass
class Traceback(Message):
    """Send data when a traceback is raised."""

    target: Target = field(default=Target.Hub, init=False)
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
    target: Target = field(default=Target.Tracking | Target.Playback | Target.Hub, init=False)


@dataclass
class TrackingStarted(Message):
    """Send a message after tracking has started."""
    target: Target = field(default=Target.Processing | Target.GUI, init=False)


@dataclass
class PlaybackStarted(Message):
    """Sent when the playback component begins replaying events."""
    target: Target = field(default=Target.Hub | Target.GUI | Target.Processing, init=False)


@dataclass
class PlaybackStopping(Message):
    """Sent during the playback stop process."""
    target: Target = field(default=Target.Processing, init=False)


@dataclass
class PlaybackStopped(Message):
    """Sent once the playback has successfully stopped."""
    target: Target = field(default=Target.GUI, init=False)


@dataclass
class PlaybackResumeRender(Message):
    """Notification sent once a render has been received so playback can continue."""
    target: Target = field(default=Target.Playback, init=False)


@dataclass
class PlaybackFinished(Message):
    """Sent when the playback component has finished replaying events."""
    target: Target = field(default=Target.Hub | Target.GUI | Target.Processing | Target.Tracking, init=False)


@dataclass
class PauseTracking(Message):
    """Send a request to pause tracking."""
    target: Target = field(default=Target.Hub | Target.Tracking | Target.Playback | Target.GUI, init=False)


@dataclass
class StopTracking(Message):
    """Send a request to stop tracking."""
    target: Target = field(default=Target.Hub | Target.Tracking | Target.Playback | Target.Processing | Target.AppDetection | Target.GUI, init=False)


@dataclass
class MonitorsChanged(Message):
    """Send the location of each monitor when the setup changes."""

    target: Target = field(default=Target.GUI | Target.Processing | Target.Playback, init=False)
    data: MonitorData


@dataclass
class RenderRequest(Message):
    """Request a render.

    If profile is None then the currently loaded profile will be
    rendered.
    """

    target: Target = field(default=Target.Processing | Target.Playback, init=False)
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
    show_keyboard_time: bool = False
    interpolation_order: Literal[0, 1, 2, 3, 4, 5] = 0
    layer_visible: bool = True
    allow_empty_render: bool = False


@dataclass
class Render(Message):
    """A render has been completed."""

    target: Target = field(default=Target.GUI | Target.Playback, init=False)
    array: npt.NDArray[np.uint8]
    request: RenderRequest



@dataclass
class RequestRunningAppCheck(Message):
    """Check which applications are running."""

    target: Target = field(default=Target.AppDetection, init=False)


@dataclass
class TrackedApplicationDetected(Message):
    """Detect when a new tracked application is focused.

    This was originally processed by all components, but there was a
    rare chance of a race condition where the active time was 1 tick
    higher than the elapsed time. Now it notifies just the tracking
    component, which then it turn sends a separate message out to the
    other components, but in sync with the ticks.
    """

    target: Target = field(default=Target.Tracking, init=False)
    name: str
    process_id: int | None
    rects: RectList = field(default_factory=RectList)


@dataclass
class CurrentProfileChanged(Message):
    """Trigger a profile switch.

    This is a variation of `TrackedApplicationDetected`, but is in
    sync with the tick counter to prevent race conditions.
    """

    target: Target = field(default=Target.Processing | Target.GUI | Target.Playback, init=False)
    name: str
    process_id: int | None
    rects: RectList = field(default_factory=RectList)


@dataclass
class ApplicationFocusChanged(Message):
    """Send a notification whenever a new application is focused.
    This is for debugging and is not used for logic.
    """

    target: Target = field(default=Target.GUI, init=False)
    exe: str
    title: str
    tracked: bool



@dataclass
class Exit(Message):
    """Quit the whole application."""

    target: Target = field(default=Target.Hub | Target.Tracking | Target.Playback | Target.Processing | Target.AppDetection | Target.GUI, init=False)


@dataclass
class DebugRaiseError(Message):
    """Raise an error for debugging."""


@dataclass
class ProcessShutDownNotification(Message):
    """Send a notification from a process that it has ended."""
    target: Target = field(default=Target.Hub, init=False)
    source: Target


@dataclass
class Save(Message):
    """Once a save is ready to be done."""

    target: Target = field(default=Target.Processing, init=False)
    profile_name: str | None = None


@dataclass
class SaveComplete(Message):
    """After a profile has been saved."""

    target: Target = field(default=Target.GUI, init=False)
    succeeded: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)


@dataclass
class ProfileDataRequest(Message):
    target: Target = field(default=Target.Processing, init=False)
    sanitised_name: str
    profile_name: str


@dataclass
class ProfileData(Message):
    """Information about a profile."""

    target: Target = field(default=Target.GUI, init=False)
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

    target: Target = field(default=Target.Processing | Target.GUI | Target.Playback, init=False)
    mac_address: str
    bytes_sent: int
    bytes_recv: int


@dataclass
class Active(Message):

    target: Target = field(default=Target.Processing | Target.GUI, init=False)
    profile_name: str
    ticks: int


@dataclass
class Inactive(Message):

    target: Target = field(default=Target.Processing | Target.GUI, init=False)
    profile_name: str
    ticks: int


@dataclass
class SetProfileTracking(Message):
    target: Target = field(default=Target.Processing, init=False)
    profile_name: str
    device: Device
    enable: bool


@dataclass
class SetGlobalTracking(Message):
    target: Target = field(default=Target.Tracking, init=False)
    device: Device
    enable: bool


@dataclass
class DebugDisableAppDetection(Message):
    target: Target = field(default=Target.Tracking, init=False)
    disable: bool


@dataclass
class DebugDisableMonitorCheck(Message):
    target: Target = field(default=Target.Tracking, init=False)
    disable: bool


@dataclass
class DeleteData(Message):
    target: Target = field(default=Target.Processing, init=False)
    profile_name: str
    devices: Device


@dataclass
class DeleteProfile(Message):
    target: Target = field(default=Target.Processing, init=False)
    profile_name: str


@dataclass
class Autosave(Message):
    target: Target = field(default=Target.Tracking, init=False)
    enabled: bool


@dataclass
class RequestQueueSize(Message):
    target: Target = field(default=Target.Hub, init=False)


@dataclass
class QueueSize(Message):
    target: Target = field(default=Target.GUI, init=False)
    hub: int
    tracking: int
    processing: int
    gui: int
    app_detection: int
    playback: int


@dataclass
class ToggleConsole(Message):
    """Change the visible state of the console."""
    target: Target = field(default=Target.Hub | Target.GUI, init=False)
    show: bool


@dataclass
class InvalidConsole(Message):
    """Triggered if the console is determined to be not valid.
    This may be the built in console in an IDE for example.
    """
    target: Target = field(default=Target.GUI, init=False)


@dataclass
class ImportProfile(Message):
    """Send a request to import a profile."""

    target: Target = field(default=Target.Processing | Target.GUI, init=False)
    name: str
    path: str


@dataclass
class ImportLegacyProfile(Message):
    """Send a request to import a legacy profile."""

    target: Target = field(default=Target.Processing | Target.GUI, init=False)
    name: str
    path: str


@dataclass
class FailedProfileImport(Message):
    """Send a request to import a legacy profile."""

    target: Target = field(default=Target.GUI, init=False)
    request: ImportProfile | ImportLegacyProfile


@dataclass
class ExportStats(Message):
    target: Target = field(default=Target.Processing, init=False)
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

    target: Target = field(default=Target.GUI, init=False)
    request: ExportStats


@dataclass
class HistoryExported(Message):
    """Notify the GUI that a history export has been saved successfully."""

    target: Target = field(default=Target.GUI, init=False)
    path: str
    duration_ticks: int


@dataclass
class ReloadAppList(Message):
    """Reload AppList.txt."""

    target: Target = field(default=Target.AppDetection | Target.GUI, init=False)


@dataclass
class ToggleProfileResolution(Message):
    """Enable or disable a resolution for a profile."""

    target: Target = field(default=Target.Processing, init=False)
    profile: str
    resolution: tuple[int, int]
    enable: bool


@dataclass
class ToggleProfileMultiMonitor(Message):
    """Change multi monitor handling for a profile."""

    target: Target = field(default=Target.Processing, init=False)
    profile: str
    multi_monitor: bool | None


@dataclass
class RequestPID(Message):
    """Request a components PID."""


@dataclass
class SendPID(Message):
    """Send a components PID."""

    target: Target = field(default=Target.GUI, init=False)
    source: Target
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

    target: Target = field(default=Target.Processing, init=False)
    layers: list[RenderLayer]


@dataclass
class ComponentLoaded(Message):
    """Notify when a single component has loaded."""

    target: Target = field(default=Target.Hub, init=False)
    component: Target


@dataclass
class AllComponentsLoaded(Message):
    """Notify once every component has been loaded."""

    target: Target = field(default=Target.Hub | Target.GUI | Target.Playback, init=False)


@dataclass
class ShowPopup(Message):
    """Trigger a popup message in the GUI."""

    target: Target = field(default=Target.GUI, init=False)
    content: str


@dataclass
class SetHistoryLength(Message):
    """Set the history window in ticks. 0 disables caching and clears history."""

    target: Target = field(default=Target.Playback, init=False)
    ticks: int


@dataclass
class ExportHistory(Message):
    """Export a slice of the history buffer to a .jsonl.gz file."""

    target: Target = field(default=Target.Playback, init=False)
    path: str
    start_percentage: float
    end_percentage: float


@dataclass
class PlaybackOptions(Message):
    """Configure playback settings before or during playback."""

    target: Target = field(default=Target.Playback, init=False)
    ups: float
    skip_empty_ticks: bool
    start_percentage: float
    end_percentage: float


@dataclass
class StartPlayback(Message):
    """Start replaying the buffered history."""

    target: Target = field(default=Target.Playback, init=False)
    options: PlaybackOptions


@dataclass
class StopPlayback(Message):
    """Stop history playback mode."""

    target: Target = field(default=Target.Hub | Target.Playback | Target.Tracking, init=False)


@dataclass
class PausePlayback(Message):
    """Pause history playback."""

    target: Target = field(default=Target.Playback, init=False)


@dataclass
class ResumePlayback(Message):
    """Resume a paused history playback."""

    target: Target = field(default=Target.Playback, init=False)


@dataclass
class RequestPlaybackProgress(Message):
    """Request the current playback position."""

    target: Target = field(default=Target.Playback, init=False)


@dataclass
class PlaybackProgress(Message):
    """Current playback position within the history range."""

    target: Target = field(default=Target.GUI, init=False)
    percentage: float


@dataclass
class StartRecording(Message):
    """Record tracking messages to a specific path."""

    target: Target = field(default=Target.Hub | Target.Processing, init=False)
    path: str


@dataclass
class StopRecording(Message):
    """Finish recording messages."""

    target: Target = field(default=Target.Hub, init=False)


@dataclass
class RecordingComplete(Message):
    """Notify GUI that recording has been saved successfully."""

    target: Target = field(default=Target.GUI, init=False)


@dataclass
class RequestHistoryLength(Message):
    """Request the current amount of recorded ticks."""

    target: Target = field(default=Target.Playback, init=False)


@dataclass
class HistoryLength(Message):
    """Send the current amount of recorded ticks."""

    target: Target = field(default=Target.GUI, init=False)
    ticks: int

