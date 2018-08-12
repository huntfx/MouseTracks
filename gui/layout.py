"""This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""

from __future__ import absolute_import

import core.qt.wrappers as QtCustom
from ext.Qt import QtWidgets, QtCore

def setup_layout(parent):
    QtCustom.Parent.set(parent)

    with QtCustom.LayoutResizableV():
        with QtCustom.LayoutBoxH() as program_layout:
            program_layout.setContentsMargins(left=0)
            program_layout.setSpacing(6)

            QtCustom.QLabel('Image goes here')
            with QtCustom.WidgetTabGroup() as tab_group:
                tab_group.setFixedWidth(278)
                with QtCustom.TabScrollLayout('Render Options'):
                    
                    with QtCustom.WidgetGroupBox('Profile Selection'):
                        with QtCustom.LayoutBoxV():
                            dropdown = QtCustom.QComboBox()
                            dropdown.addItems(['<current>', 'Default', 'Overwatch', 'Path of Exile'])

                    with QtCustom.WidgetGroupBox('Image Options'):
                        with QtCustom.LayoutBoxV():
                            QtCustom.QComboBox().addItems(['Tracks', 'Clicks', 'Acceleration', 'Keyboard'])
                            dropdown = QtCustom.QComboBox()
                            dropdown.addItems(['Time', 'Count'])
                            dropdown.setVisible(False)

                    with QtCustom.WidgetGroupBox('Colour Options'):
                        with QtCustom.LayoutBoxV():
                            with QtCustom.LayoutBoxH():
                                QtCustom.QLineEdit('Demon')
                                dropdown = QtCustom.QComboBox()
                                dropdown.addItems(['Presets', 'Citrus', 'Demon', 'Sunburst'])

                    with QtCustom.WidgetGroupBox('Saving'):
                        with QtCustom.LayoutBoxV():
                            QtCustom.QCheckBox('Only show current session')
                            with QtCustom.LayoutBoxH():
                                QtCustom.QPushButton('Save Image')
                                QtCustom.QStretch()
                                QtCustom.QPushButton('Export Data')

                    with QtCustom.WidgetGroupBox('Show/Hide Mouse Buttons'):
                        with QtCustom.LayoutBoxV():
                            checkbox = QtCustom.QCheckBox('Left Mouse Button')
                            checkbox.setChecked(True)
                            checkbox = QtCustom.QCheckBox('Middle Mouse Button')
                            checkbox.setChecked(True)
                            checkbox = QtCustom.QCheckBox('Right Mouse Button')
                            checkbox.setChecked(True)

                    QtCustom.QStretch()

                with QtCustom.TabScrollLayout('Advanced'):
                    with QtCustom.WidgetGroupBox('Custom Tracking Groups'):
                        with QtCustom.LayoutBoxV():
                            with QtCustom.LayoutBoxH():
                                QtCustom.QLineEdit('<Default>')
                                QtCustom.QPushButton('Apply')
                            QtCustom.QCheckBox('Set as default for current profile')
                            QtCustom.QCheckBox('Keep this group active on profile switch')
                            QtCustom.QCheckBox('Disable profile switching')
                    QtCustom.QStretch()

        list_widget = QtCustom.QListWidget()
        list_widget.addItems(['test'])