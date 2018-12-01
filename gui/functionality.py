
"""This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""

from __future__ import absolute_import

from ext.Qt import QtWidgets, QtCore, QtGui
from gui.layout import MainWindowLayout


class ImageViewer(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        QtWidgets.QWidget.__init__(self, parent)

        self.image_label = QtWidgets.QLabel()
        self.image_label.setBackgroundRole(QtGui.QPalette.Base)
        self.image_label.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Ignored)
        self.image_label.setScaledContents(True)

    def open(self, filename):
        if filename:
            image = QtGui.QImage(filename)
            if image.isNull():
                QtWidgets.QMessageBox.information(self, 'Image Viewer', 'Cannot load {}'.format(filename))
                return
            self.image_label.setPixmap(QtGui.QPixmap(image))
