"""Entry point for MouseTracks 2."""

import sys
from multiprocessing import freeze_support


if __name__ == '__main__':
    freeze_support()

    while True:
        try:
            # We import inside the loop so the module namespace is re-evaluated if possible
            from mousetracks2.__main__ import main
            main()

        except Exception:  # pylint: disable=broad-exception-caught
            exc_type, exc_val, exc_tb = sys.exc_info()
            assert exc_type is not None and exc_val is not None and exc_tb is not None

            from mousetracks2.popups import show_error_dialog
            if not show_error_dialog(exc_type, exc_val, exc_tb):
                sys.exit(1)

        else:
            break
