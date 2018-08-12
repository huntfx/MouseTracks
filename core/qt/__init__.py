from __future__ import absolute_import

import os

from ext.Qt import QtWidgets, QtCore, QtGui


class Clipboard(object):
    def __init__(self):
        self.cb = QtWidgets.QApplication.clipboard()
        self.mode = self.cb.Clipboard
    
    def write(self, text):
        self.cb.clear(mode=self.mode)
        self.cb.setText(str(text), mode=self.mode)

    def read(self):
        return self.cb.text()


class FileDialogue(object):
    WORKING_DIR = os.getcwd()
    
    def __init__(self, parent=None, default_dir=WORKING_DIR):
        self.parent = parent
        self._dir = default_dir

    def select_directory(self, title='Select Folder'):
        return QtWidgets.QFileDialog.getExistingDirectory(self.parent, title, self._dir, QtWidgets.QFileDialog.ShowDirsOnly)