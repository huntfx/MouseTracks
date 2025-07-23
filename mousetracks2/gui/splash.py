import sys
from typing import Self

from PySide6 import QtCore, QtGui, QtWidgets

from .utils import ICON_PATH


class SplashScreen(QtWidgets.QSplashScreen):
    """Basic splash screen to show while the application is loading.
    This must be in the same process as the main GUI, as otherwise it
    will cause issues on Linux.
    """

    def __init__(self, icon_path: str = ICON_PATH) -> None:
        """Launch the splash screen."""
        pixmap = QtGui.QPixmap(icon_path)
        super().__init__(pixmap)
        self.setWindowFlags(QtCore.Qt.WindowType.SplashScreen
                            | QtCore.Qt.WindowType.FramelessWindowHint
                            | QtCore.Qt.WindowType.WindowStaysOnTopHint)
        self.setMask(pixmap.mask())
        self.show()
