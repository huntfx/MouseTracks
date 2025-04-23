import os

from PySide6 import QtCore, QtWidgets, QtGui

from .ui import applist


class AppListWindow(QtWidgets.QDialog):
    def __init__(self, parent: QtWidgets.QWidget) -> None:
        super().__init__(parent)

        self.ui = applist.Ui_Form()
        self.ui.setupUi(self)
        self.ui.advanced.setChecked(False)

        self.ui.executable.currentTextChanged.connect(self.update_profile_suggestion)
        self.ui.window_title.textChanged.connect(self.update_profile_suggestion)
        self.ui.window_title_enabled.toggled.connect(self.update_profile_suggestion)

    @QtCore.Slot()
    def update_profile_suggestion(self) -> None:
        """Update the default profile name."""
        if self.ui.window_title_enabled.isChecked() and self.ui.window_title.text():
            self.ui.profile_name.setPlaceholderText(self.ui.window_title.text())
        else:
            self.ui.profile_name.setPlaceholderText(os.path.splitext(self.ui.executable.currentText())[0])
