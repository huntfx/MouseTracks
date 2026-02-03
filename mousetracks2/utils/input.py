import pynput


def get_cursor_pos() -> tuple[int, int] | None:
    """Get the current cursor position.

    This is only used for switching profiles, as the mouse move listener
    can handle all other events.
    """
    pos = pynput.mouse.Controller().position
    if pos is None:
        return None
    return int(pos[0]), int(pos[1])
