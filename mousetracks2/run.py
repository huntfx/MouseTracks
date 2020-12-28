import sys
import os
sys.path.append(os.path.dirname(__file__))

from gui import MainWindow
from track import run


if __name__ == '__main__':
    MainWindow.show(run)
