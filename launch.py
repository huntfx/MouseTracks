"""Entry point for MouseTracks 2."""

import sys
import traceback
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

            from mousetracks2.utils.crash import show_error_dialog
            if not show_error_dialog(exc_type, exc_val, exc_tb):
                sys.exit(1)

        else:
            break
