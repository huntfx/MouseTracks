import webbrowser

from PySide6 import QtCore, QtWidgets

from .ui import about
from ..version import __version__


class AboutWindow(QtWidgets.QDialog):
    """Show an "about" window with the current version."""

    def __init__(self, parent: QtWidgets.QWidget) -> None:
        super().__init__(parent)
        self.ui = about.Ui_Dialog()
        self.ui.setupUi(self)
        self.ui.version.setText(f'<span style=" font-size:10pt;">Version {__version__} '
                                f'(<a href="https://github.com/huntfx/MouseTracks/releases/tag/v{__version__}">'
                                'release notes</a>)</span>')
        self.ui.version.linkActivated.connect(self.loadReleaseNotes)

    @QtCore.Slot(str)
    def loadReleaseNotes(self, url: str) -> None:
        """Load the page to the release notes."""
        webbrowser.open(url)
