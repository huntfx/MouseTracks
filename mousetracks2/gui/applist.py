import os

import psutil
from PySide6 import QtCore, QtWidgets

from .ui import applist
from ..applications import AppList
from ..constants import TRACKING_IGNORE, TRACKING_DISABLE


class AppListWindow(QtWidgets.QDialog):
    """Interface to the AppList.txt file."""

    def __init__(self, parent: QtWidgets.QWidget) -> None:
        super().__init__(parent)
        self.applist = AppList()
        self._previous_exe_rules: str = ''

        self.ui = applist.Ui_Form()
        self.ui.setupUi(self)
        self.ui.advanced.setChecked(False)

        self.ui.save.clicked.connect(self.save)
        self.ui.executable.currentTextChanged.connect(self.update_profile_suggestion)
        self.ui.executable.currentTextChanged.connect(self.update_matching_apps)
        self.ui.executable.currentIndexChanged.connect(self.executable_changed)
        self.ui.window_title.textChanged.connect(self.update_profile_suggestion)
        self.ui.window_title_enabled.toggled.connect(self.update_profile_suggestion)
        self.ui.rules.itemClicked.connect(self.selected_new_rule)
        self.ui.create.clicked.connect(self.create_new_rule)
        self.ui.remove.clicked.connect(self.remove_selected_rule)

        self._populate_process_list()

    def _populate_process_list(self) -> None:
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

    @QtCore.Slot(int)
    def executable_changed(self, index: int) -> None:
        """Reset data to default when the executable is changed."""
        self.ui.window_title.setText('')
        self.ui.window_title_enabled.setChecked(False)
        self.ui.profile_name.setText('')
        self.ui.state_enabled.setChecked(True)

    @QtCore.Slot()
    def update_profile_suggestion(self) -> None:
        """Update the default profile name."""
        if self.ui.window_title_enabled.isChecked() and self.ui.window_title.text():
            self.ui.profile_name.setPlaceholderText(self.ui.window_title.text())
        else:
            self.ui.profile_name.setPlaceholderText(os.path.splitext(self.ui.executable.currentText())[0])

    @QtCore.Slot()
    def update_matching_apps(self, force: bool = False) -> None:
        """Load in the profile data."""
        exe = self.ui.executable.currentText()
        if not force and exe == self._previous_exe_rules:
            return
        self._previous_exe_rules = exe

        self.ui.rules.clear()
        self.ui.remove.setEnabled(False)
        for data, executable in self.applist._match_exe(self._previous_exe_rules, full_paths=True):
            for window_title, profile_name in data.items():
                if window_title is None:
                    if profile_name == os.path.splitext(os.path.basename(executable))[0]:
                        name = executable
                    else:
                        name = f'{executable}: {profile_name}'
                elif profile_name == window_title:
                    name = f'{executable}[{window_title}]'
                else:
                    name = f'{executable}[{window_title}]: {profile_name}'

                item = QtWidgets.QListWidgetItem(name)
                item.setData(QtCore.Qt.ItemDataRole.UserRole, (executable, window_title, profile_name))
                self.ui.rules.addItem(item)
        self.ui.rules.sortItems()

    @QtCore.Slot()
    def create_new_rule(self) -> None:
        """Create or update a rule with the current data."""
        # Read data
        executable = self.ui.executable.currentText()
        if self.ui.window_title_enabled.isChecked():
            window_title = self.ui.window_title.text()
        else:
            window_title = None
        profile_name = self.ui.profile_name.text() or self.ui.profile_name.placeholderText()

        # Update rule
        self.applist.data[executable][window_title] = profile_name

        # Reload rules list
        self.update_matching_apps(force=True)

        # Select item
        for item in map(self.ui.rules.item, range(self.ui.rules.count())):
            if (executable, window_title, profile_name) == item.data(QtCore.Qt.ItemDataRole.UserRole):
                self.ui.rules.setCurrentItem(item)
                self.ui.remove.setEnabled(True)
                break

    @QtCore.Slot(QtWidgets.QListWidgetItem)
    def selected_new_rule(self, current: QtWidgets.QListWidgetItem) -> None:
        """Load the selected rule into the input boxes.

        Note that if `itemSelectionChanged` is used then it will cause a
        crash on clear - https://stackoverflow.com/a/20759098/2403000.
        """
        self.ui.remove.setEnabled(True)

        # Get data from item
        executable, window_title, profile_name = current.data(QtCore.Qt.ItemDataRole.UserRole)

        # Set executable
        self.ui.executable.setCurrentText(executable)

        # Set window title
        if window_title is None:
            self.ui.window_title_enabled.setChecked(False)
            self.ui.window_title.setText('')
        else:
            self.ui.window_title_enabled.setChecked(True)
            self.ui.window_title.setText(window_title)
            self.ui.advanced.setChecked(True)

        # Set state
        if profile_name == TRACKING_IGNORE:
            self.ui.state_ignored.setChecked(True)
            self.ui.profile_name.setText('')
            self.ui.advanced.setChecked(True)
        elif profile_name == TRACKING_DISABLE:
            self.ui.state_disabled.setChecked(True)
            self.ui.profile_name.setText('')
            self.ui.advanced.setChecked(True)
        else:
            self.ui.state_enabled.setChecked(True)
            if window_title is None:
                if os.path.splitext(os.path.basename(executable))[0] == profile_name:
                    self.ui.profile_name.setText('')
            elif window_title == profile_name:
                self.ui.profile_name.setText('')
            else:
                self.ui.profile_name.setText(profile_name)

    @QtCore.Slot()
    def remove_selected_rule(self) -> None:
        """Remove the selected rule."""
        for item in self.ui.rules.selectedItems():
            executable, window_title, profile_name = item.data(QtCore.Qt.ItemDataRole.UserRole)
            del self.applist.data[executable][window_title]
        self.update_matching_apps(force=True)

    def save(self) -> None:
        """Save the data and exit."""
        self.applist.save()
        self.accept()
