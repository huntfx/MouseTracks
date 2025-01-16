import sys
from pathlib import Path
from multiprocessing import freeze_support

# Source DLL files when running as an executable
if hasattr(sys, '_MEIPASS'):
    sys.path.append(str(Path(__file__).parent / 'resources' / 'build'))

from mousetracks2.components.hub import Hub


if __name__ == '__main__':
    freeze_support()
    Hub().run(gui=True)
