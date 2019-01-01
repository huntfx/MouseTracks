from __future__ import absolute_import, division

from ..utils.qt.Qt import QtWidgets, QtCore, QtGui
from ..utils.qt.main import QtRoot
from ..utils.qt import widgets as QtCustom


def setup_layout(parent):
    with QtRoot(parent) as container_layout:
        with container_layout.addVSplitter() as main_layout:
            with main_layout.addLayout(QtWidgets.QHBoxLayout()) as program_layout:
                
                program_layout.setContentsMargins(0)
                program_layout.setSpacing(0)
                program_layout.addWidget(QtCustom.ResizableImage(None, pixmap='images/test.jfif'))
                
                with program_layout.addTabGroup() as tab_group_layout:
                    tab_group_layout.setFixedWidth(278)

                    with tab_group_layout.addTab(QtWidgets.QVBoxLayout(), 'Render Options') as (tab_widget, tab_layout):
                        tab_widget.setContentsMargins(0)

                        with tab_layout.addScrollArea(QtWidgets.QVBoxLayout()) as (scroll_widget, scroll_layout):

                            with scroll_layout.addGroupBox(QtWidgets.QVBoxLayout(), 'Profile Selection') as (group_widget, group_layout):
                                dropdown = group_layout.addWidget(QtWidgets.QComboBox())
                                dropdown.addItems(['<current>', 'Default', 'Overwatch', 'Path of Exile'])

                            with scroll_layout.addGroupBox(QtWidgets.QVBoxLayout(), 'Image Options') as (group_widget, group_layout):
                                dropdown = group_layout.addWidget(QtWidgets.QComboBox())
                                dropdown.addItems(['Tracks', 'Clicks', 'Acceleration', 'Keyboard'])
                                dropdown = group_layout.addWidget(QtWidgets.QComboBox())
                                dropdown.addItems(['Time', 'Count'])
                                dropdown.setVisible(False)

                            with scroll_layout.addGroupBox(QtWidgets.QVBoxLayout(), 'Colour Options') as (group_widget, group_layout):
                                with group_layout.addLayout(QtWidgets.QHBoxLayout()) as horizontal_layout:
                                    horizontal_layout.addWidget(QtWidgets.QLineEdit('Citrus'))
                                    dropdown = horizontal_layout.addWidget(QtWidgets.QComboBox())
                                    dropdown.addItems(['Presets', 'Citrus', 'Demon', 'Sunburst'])

                            with scroll_layout.addGroupBox(QtWidgets.QVBoxLayout(), 'Saving') as (group_widget, group_layout):
                                group_layout.addWidget(QtWidgets.QCheckBox('Only show current session'))
                                with group_layout.addLayout(QtWidgets.QHBoxLayout()) as horizontal_layout:
                                    horizontal_layout.addWidget(QtWidgets.QPushButton('Save Image'))
                                    horizontal_layout.addStretch()
                                    export = horizontal_layout.addWidget(QtWidgets.QPushButton('Export Data'))
                                    export.setEnabled(False)

                            with scroll_layout.addGroupBox(QtWidgets.QVBoxLayout(), 'Show/Hide Mouse Buttons') as (group_widget, group_layout):
                                lmb = group_layout.addWidget(QtWidgets.QCheckBox('Left Mouse Button'))
                                lmb.setChecked(True)
                                mmb = group_layout.addWidget(QtWidgets.QCheckBox('Middle Mouse Button'))
                                mmb.setChecked(True)
                                rmb = group_layout.addWidget(QtWidgets.QCheckBox('Right Mouse Button'))
                                rmb.setChecked(True)

                            scroll_layout.addStretch()

                    with tab_group_layout.addTab(QtWidgets.QVBoxLayout(), 'Advanced') as (tab_widget, tab_layout):
                        tab_widget.setContentsMargins(0)

                        with tab_layout.addScrollArea(QtWidgets.QVBoxLayout()) as (scroll_widget, scroll_layout):

                            with scroll_layout.addGroupBox(QtWidgets.QVBoxLayout(), 'Custom Tracking Groups') as (group_widget, group_layout):
                                with group_layout.addLayout(QtWidgets.QHBoxLayout()) as horizontal_layout:
                                    horizontal_layout.addWidget(QtWidgets.QLineEdit('<default>'))
                                    horizontal_layout.addWidget(QtWidgets.QPushButton('Apply'))
                                group_layout.addWidget(QtWidgets.QCheckBox('Set as default for current profile'))
                                group_layout.addWidget(QtWidgets.QCheckBox('Keep this group active on profile switch'))
                                group_layout.addWidget(QtWidgets.QCheckBox('Disable profile switching'))

                            scroll_layout.addStretch()
            
            lw = main_layout.addWidget(QtWidgets.QListWidget())
            lw.addItems(['console output'])