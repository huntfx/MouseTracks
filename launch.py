"""Entry point for Mousetracks 2, with error handling.

Usage: `python launch.py`
"""

import sys
from multiprocessing import freeze_support


if __name__ == '__main__':
    freeze_support()

    try:
        from mousetracks2.__main__ import main
        main()

    # Show any errors as the app otherwise will just silently fail
    except Exception:  # pylint: disable=broad-exception-caught
        import traceback
        traceback.print_exc()
        input('Press enter to exit...')
        sys.exit(1)
