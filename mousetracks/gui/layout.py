from __future__ import absolute_import

from ..utils.qt2.Qt import QtWidgets, QtCore
from ..utils import qt2 as QtCustom


def setup_layout(parent):
    
    '''
    main_layout = QtWidgets.QVBoxLayout()
    parent.setCentralWidget(QtCustom.layoutToWidget(main_layout))

    main_layout.addWidget(QtWidgets.QCheckBox())
    '''

    '''
    __init__(self, func, parent)
        parent.setCentralWidget(layoutToWidget(self))

    addWidget(self, widget):
        self.QObject.addWidget
    '''
    with QtCustom.QtLayout(QtWidgets.QVBoxLayout(), parent) as main_layout:
        with main_layout.addLayout(QtWidgets.QHBoxLayout()) as program_layout:
            program_layout.addWidget(QtWidgets.QPushButton('what'))
            program_layout.addWidget(QtWidgets.QPushButton('what'))
        main_layout.addWidget(QtWidgets.QPushButton('yes'))
        main_layout.addWidget(QtCustom.QCheckBox('yes'))

    '''
    with parent.addLayout(QtCustom.LayoutResizableV()) as main_layout:
        with main_layout.addLayout(QtCustom.LayoutBoxH()) as program_layout:
            program_layout.setContentsMargins(left=0)
            program_layout.setSpacing(6)

            program_layout.addWidget(QtCustom.QLabel('Image goes here'))
            with program_layout.addLayout(QtCustom.WidgetTabGroup()) as tab_group:
                tab_group.setFixedWidth(278)
                with tab_group.addLayout(QtCustom.TabScrollLayout('Render Options')) as render_options:
                    
                    with render_options.addLayout(QtCustom.WidgetGroupBox('Profile Selection'), QtCustom.LayoutBoxV()) as group_box, vertical_layout:
                        dropdown = vertical_layout.addWidget(QtCustom.QComboBox())
                        dropdown.addItems(['<current>', 'Default', 'Overwatch', 'Path of Exile'])

'''