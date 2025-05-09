import os

import psutil
from PySide6 import QtCore, QtWidgets, QtGui

from .ui import applist
from ..applications import AppList
from ..constants import TRACKING_IGNORE, TRACKING_DISABLE


class AppListWindow(QtWidgets.QDialog):
    def __init__(self, parent: QtWidgets.QWidget) -> None:
        super().__init__(parent)
        self.applist = AppList()
        self._previous_exe_rules: str = ''

        self.ui = applist.Ui_Form()
        self.ui.setupUi(self)
        self.ui.advanced.setChecked(False)

        self.ui.executable.currentTextChanged.connect(self.update_profile_suggestion)
        self.ui.executable.currentTextChanged.connect(self.update_matching_apps)
        self.ui.window_title.textChanged.connect(self.update_profile_suggestion)
        self.ui.window_title_enabled.toggled.connect(self.update_profile_suggestion)
        self.ui.rules.currentItemChanged.connect(self.selected_new_rule)

        self._populate_proc_list()

    def _populate_proc_list(self) -> None:
        """Load in the list of all processes."""
        self.ui.executable.clear()

        seen = set()
        for proc in reversed(tuple(psutil.process_iter(attrs=['exe']))):
            path = proc.info['exe']
            if path is None:
                continue
            exe = os.path.basename(path)
            if exe in seen:
                continue
            seen.add(exe)
            self.ui.executable.addItem(exe)

    @QtCore.Slot()
    def update_profile_suggestion(self) -> None:
        """Update the default profile name."""
        if self.ui.window_title_enabled.isChecked() and self.ui.window_title.text():
            self.ui.profile_name.setPlaceholderText(self.ui.window_title.text())
        else:
            self.ui.profile_name.setPlaceholderText(os.path.splitext(self.ui.executable.currentText())[0])

    @QtCore.Slot()
    def update_matching_apps(self) -> None:
        """Load in the profile data."""
        exe = self.ui.executable.currentText()
        if exe == self._previous_exe_rules:
            return
        self._previous_exe_rules = exe

        self.ui.rules.clear()
        for data, executable in self.applist._match_exe(exe, full_paths=True):
            for window_title, profile_name in data.items():
                if window_title is None:
                    if profile_name == os.path.basename(executable):
                        name = executable
                    else:
                        name = f'{executable}: {profile_name}'
                elif profile_name == os.path.basename(executable):
                    name = f'{executable}[{window_title}]'
                else:
                    name = f'{executable}[{window_title}]: {profile_name}'

                item = QtWidgets.QListWidgetItem(name)
                item.setData(QtCore.Qt.UserRole, (executable, window_title, profile_name))
                self.ui.rules.addItem(item)
        self.ui.rules.sortItems()

    @QtCore.Slot(QtWidgets.QListWidgetItem, QtWidgets.QListWidgetItem)
    def selected_new_rule(self, current: QtWidgets.QListWidgetItem | None,
                          previous: QtWidgets.QListWidgetItem | None) -> None:
        """Load the selected rule into the input boxes."""
        if current is None:
            return
        # Get data from item
        executable, window_title, profile_name = current.data(QtCore.Qt.UserRole)

        # Set executable
        self.ui.executable.setCurrentText(executable)

        # Set window title
        if window_title is None:
            self.ui.window_title_enabled.setChecked(False)
            self.ui.window_title.setText('')
        else:
            self.ui.window_title_enabled.setChecked(True)
            self.ui.window_title.setText(window_title)

        # Set state
        if profile_name == TRACKING_IGNORE:
            self.ui.state_ignored.setChecked(True)
            self.ui.profile_name.setText('')
        elif profile_name == TRACKING_DISABLE:
            self.ui.state_disabled.setChecked(True)
            self.ui.profile_name.setText('')
        else:
            self.ui.state_enabled.setChecked(True)
            self.ui.profile_name.setText(profile_name)
