from __future__ import absolute_import

from .layout import setup_layout
from ..utils.qt.Qt import QtWidgets


class MainWindow(QtWidgets.QMainWindow):

    def __init__(self, parent=None):
        QtWidgets.QMainWindow.__init__(self, parent)
        setup_layout(self)