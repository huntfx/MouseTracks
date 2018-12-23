from __future__ import absolute_import

from .main import *

'''
class QCheckBox(QtWidget):
    def __init__(self, *args, **kwargs):
        super(QCheckBox, self).__init__(QtWidgets.QCheckBox, *args, **kwargs)
'''

class LayoutResizable(QtWidget):
    """Context manager for QSplitter."""
    def __init__(self, orientation, *args, **kwargs):
        QtWidget.__init__(self, QtWidgets.QSplitter, orientation, *args, **kwargs)


class LayoutResizableH(LayoutResizable):
    """Context manager for QSplitter set to horizontal."""
    def __init__(self, *args, **kwargs):
        LayoutResizable.__init__(self, QtCore.Qt.Horizontal, *args, **kwargs)


class LayoutResizableV(LayoutResizable):
    """Context manager for QSplitter set to vertical."""
    def __init__(self, *args, **kwargs):
        LayoutResizable.__init__(self, QtCore.Qt.Vertical, *args, **kwargs)