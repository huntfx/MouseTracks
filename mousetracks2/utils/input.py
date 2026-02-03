import pynput


def get_cursor_pos() -> tuple[int, int] | None:
    """Get the current cursor position.

    This is only used for switching profiles, as the mouse move listener
    can handle all other events.
    """
    return pynput.mouse.Controller().position
