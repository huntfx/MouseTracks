from __future__ import absolute_import
import sys
#from PyQt5.QtWidgets import QApplication, QWidget, QDesktopWidget

from ext.Qt import QtWidgets
from gui.layout import MainWindowLayout
import sys


class MainWindow(QtWidgets.QMainWindow):

    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)

        self.layout = MainWindowLayout()
        self.layout.setup(self)


if __name__ == "__main__":

    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    app.setActiveWindow(window) 
    window.show()
    
    sys.exit(app.exec_())
    #"C:\Users\Peter\AppData\Local\Programs\Python\Python36\python.exe" ui.py
