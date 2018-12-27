from __future__ import absolute_import

import sys

from mousetracks.gui.connect import MainWindow
from mousetracks.utils.qt.Qt import QtWidgets


if __name__ == "__main__":

    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    app.setActiveWindow(window) 
    window.show()
    
    sys.exit(app.exec_())