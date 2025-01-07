from dataclasses import dataclass
from typing import Optional

from PySide6 import QtCore, QtGui, QtWidgets


@dataclass
class Pixel:
    """Pixel to update."""
    pixel: QtCore.QPoint
    colour: QtGui.QColor

    def drawTo(self, image: QtGui.QImage) -> None:
        image.setPixelColor(self.pixel, self.colour)


class ResizableImage(QtWidgets.QLabel):
    """QLabel used to display a resizable image."""

    clicked = QtCore.Signal()
    doubleClicked = QtCore.Signal()

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        self.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)
        self.setMinimumSize(1, 1)
        self.setPixmap(QtGui.QPixmap())

    def pixmapSize(self) -> QtCore.QSize:
        """Get the size of the image."""
        return self._pixmap.size()

    def setImage(self, image: QtGui.QImage) -> None:
        """Set a new image."""
        self._image = QtGui.QImage(image)
        self._pixmap.convertFromImage(image)
        super().setPixmap(self._scaledPixmap())

    def setPixmap(self, pixmap: QtGui.QPixmap) -> None:
        """Set a new pixmap."""
        self._pixmap = pixmap
        self._image: QtGui.QImage = pixmap.toImage()
        super().setPixmap(self._scaledPixmap())

    def _scaledPixmap(self, aspectRatio=QtCore.Qt.AspectRatioMode.KeepAspectRatio):
        """Scale the pixmap to the correct size."""
        if self._pixmap.isNull():
            return self._pixmap
        if self.size() == self._pixmap.size():
            return self._pixmap
        return self._pixmap.scaled(self.size(), aspectRatio, QtCore.Qt.TransformationMode.SmoothTransformation)

    def freezeScale(self):
        """Set the current size to the scaled size."""
        self.setPixmap(self._scaledPixmap())

    def updatePixels(self, *pixels: Pixel) -> None:
        """Update pixels on the image.
        It is recommended to batch the updates when possible.
        """
        if not pixels:
            return

        # Write each pixel to the image
        for pixel in pixels:
            pixel.drawTo(self._image)

        # Update the pixmap
        self._pixmap.convertFromImage(self._image)
        super().setPixmap(self._scaledPixmap())

    def resizeEvent(self, event):
        """Update the pixmap while resizing."""
        super().resizeEvent(event)
        self.setPixmap(self._pixmap)

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        """Emit a signal when the label is clicked."""
        self.clicked.emit()
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event: QtGui.QMouseEvent) -> None:
        """Emit a signal when the label is double clicked."""
        self.doubleClicked.emit()
        super().mouseDoubleClickEvent(event)
