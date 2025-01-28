import sys
from typing import Self

from PySide6 import QtCore, QtGui, QtWidgets

from .utils import ICON_PATH


class SplashScreen(QtWidgets.QSplashScreen):
    """Basic splash screen to show while the application is loading.
    For improved user experience, this is launched from the Hub, as it
    appears a lot quicker. A signal sent after the GUI is fully loaded
    will close it.
    """

    def __init__(self, icon_path: str = ICON_PATH) -> None:
        """Launch the splash screen."""
        pixmap = QtGui.QPixmap(icon_path)
        super().__init__(pixmap)
        self.setWindowFlags(QtCore.Qt.WindowType.SplashScreen | QtCore.Qt.WindowType.FramelessWindowHint)
        self.setMask(pixmap.mask())
        self.show()

    @classmethod
    def standalone(cls, icon_path: str = ICON_PATH) -> Self:
        """Launch a QApplication with the splash screen."""
        QtWidgets.QApplication(sys.argv)
        return cls(icon_path)
