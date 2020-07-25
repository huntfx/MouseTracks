from enum import Enum, auto


class ThreadState(Enum):
    """Current state of the main thread being run from the GUI."""

    Running = auto()
    Stopped = auto()
    Paused = auto()


class GUICommand(Enum):
    """Command sent from the GUI to the main thread."""

    Start = auto()
    Stop = auto()
    Pause = auto()
    Unpause = auto()
    TogglePause = auto()
    RaiseException = auto()


class ThreadEvent(Enum):
    """Event from the main thread sent to the GUI."""

    Started = auto()
    Stopped = auto()
    Paused = auto()
    Unpaused = auto()
    Exception = auto()
