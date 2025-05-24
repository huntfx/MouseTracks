import webbrowser

from PySide6 import QtCore, QtWidgets

from .ui import about
from ..update import is_latest_version
from ..version import VERSION


class AboutWindow(QtWidgets.QDialog):
    """Show an "about" window with the current version."""

    def __init__(self, parent: QtWidgets.QWidget) -> None:
        super().__init__(parent)
        self.ui = about.Ui_Dialog()
        self.ui.setupUi(self)
        self.ui.version.setText(f'<span style=" font-size:10pt;">Version {VERSION} '
                                f'(<a href="https://github.com/huntfx/MouseTracks/releases/tag/v{VERSION}">'
                                'release notes</a>)</span>')
        self.ui.latest.setText(self.ui.latest.property('text_latest' if is_latest_version() else 'text_update'))

        self.ui.version.linkActivated.connect(webbrowser.open)
        self.ui.latest.linkActivated.connect(webbrowser.open)

