import pynput

_CONTROLLER = pynput.mouse.Controller()


def get_cursor_pos() -> tuple[int, int] | None:
    """Get the current cursor position.

    This is used instead of pynput's mouse move listener, as the values
    it returns seem to be all over the place, sometimes even leaving the
    screen.
    """
    pos = _CONTROLLER.position
    if pos is None:
        return None
    return int(pos[0]), int(pos[1])
