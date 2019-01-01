from __future__ import absolute_import

from contextlib import contextmanager

from .Qt import QtWidgets, QtCore, QtGui


class ResizableImage(QtWidgets.QLabel):

    def __init__(self, pixmap=None, parent=None, minimumSize=(1, 1), align=QtCore.Qt.AlignCenter):
        super(ResizableImage, self).__init__(parent)
        self.setMinimumSize(*minimumSize)
        self.setAlignment(align)

        self._pixmapOriginal = None
        if pixmap is not None:
            self.setPixmap(pixmap)

    def resizeEvent(self, event):
        """Resize the pixmap if it exists, keeping the aspect ratio."""
        if self._pixmapOriginal is not None:
            
            #Test to make a square in the top left corner
            with self.makeEditable():
                colour = QtGui.QColor(255, 255, 255).rgb()
                for x in range(50):
                    for y in range(50):
                        self.setPixel(x, y, colour)

            size_mult = min(self.width() / self._pixmapWidth, self.height() / self._pixmapHeight)
            scaled_pixmap = self._pixmapOriginal.scaled(self._pixmapWidth * size_mult, self._pixmapHeight * size_mult, transformMode=QtCore.Qt.SmoothTransformation)
            super(ResizableImage, self).setPixmap(scaled_pixmap)

        return super(ResizableImage, self).resizeEvent(event)

    @contextmanager
    def makeEditable(self):
        """Convert the pixmap to an image to perform pixel editing operations.
        On finish, it will update the default pixmap.
        """
        if self._pixmapOriginal is not None:
            self._pixmapImage = self._pixmapOriginal.toImage()
        yield self
        if self._pixmapImage is not None:
            self.setPixmap(QtGui.QPixmap.fromImage(self._pixmapImage))

    def setPixel(self, *args, **kwargs):
        """Access the setPixel command of the pixmap."""
        if self._pixmapImage is not None:
            self._pixmapImage.setPixel(*args, **kwargs)

    def setPixmap(self, pixmap):
        """Set the pixmap and store information for resizing."""
        if isinstance(pixmap, str):
            pixmap = QtGui.QPixmap(pixmap)
        self._pixmapOriginal = pixmap
        self._pixmapWidth = pixmap.width()
        self._pixmapHeight = pixmap.height()
        self._pixmapImage = None

        #Cancel if the pixmap is empty
        if not self._pixmapWidth or not self._pixmapHeight:
            self._pixmapOriginal = None
            return

        super(ResizableImage, self).setPixmap(pixmap)