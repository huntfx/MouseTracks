from __future__ import absolute_import

from .main import layoutToWidget, Mixins
from .Qt import QtWidgets, QtCore


class QHSplitter(Mixins.AddLayout, QtWidgets.QSplitter):
    """Context manager for QSplitter set to horizontal."""
    def __init__(self, *args, **kwargs):
        QtWidgets.QSplitter.__init__(self, QtCore.Qt.Horizontal, *args, **kwargs)


class QVSplitter(Mixins.AddLayout, QtWidgets.QSplitter):
    """Context manager for QSplitter set to vertical."""
    def __init__(self, *args, **kwargs):
        QtWidgets.QSplitter.__init__(self, QtCore.Qt.Vertical, *args, **kwargs)