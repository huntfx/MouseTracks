"""Entry point for MouseTracks 2."""

import os
import sys
from multiprocessing import freeze_support

# Source DLL files when running as an executable
if hasattr(sys, '_MEIPASS'):
    sys.path.append(os.path.join(sys._MEIPASS, 'resources', 'build'))

from mousetracks2.components import Hub


if __name__ == '__main__':
    freeze_support()
    Hub(use_gui=True).run()
