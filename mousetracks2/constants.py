from enum import Enum, auto


class ThreadState(Enum):
    """Current state of the main thread being run from the GUI.

    Enums:
        Running: The thread is running and processing commands.
        Paused: The thread is running but ignoring commands.
        Stopped: The thread is not running.
    """

    Running = auto()
    Stopped = auto()
    Paused = auto()


class GUICommand(Enum):
    """Command sent from the GUI to the main thread.

    Enums:
        Start: Start the thread.
        Stop: Stop the thread.
        Pause: Pause the thread.
        Unpause: Unpause the thread.
        TogglePause: Toggle the paused state of the thread.
        RaiseException: Manually raise an exception in the thread.
            This is only meant to be used for debugging.
    """

    Start = auto()
    Stop = auto()
    Pause = auto()
    Unpause = auto()
    TogglePause = auto()
    RaiseException = auto()


class ThreadEvent(Enum):
    """Event from the main thread sent to the GUI.

    Enums:
        Started: After starting the thread.
        Stopped: Before safely exiting the thread.
        Paused: After pausing the thread.
        Unpaused: After unpausing the thread.
        Exception: Before an exception is raised.
            The thread will shut down if this occurrs.
        MouseMove: After moving the mouse.
            The purpose is for the GUI to update a preview image.
            Arguments:
                (x, y): Tuple of mouse position coordinates.
                    Each coordinate is within a range of 0 to 1, where
                    (0, 0) is top left.
    """

    Started = auto()
    Stopped = auto()
    Paused = auto()
    Unpaused = auto()
    Exception = auto()
    MouseMove = auto()
