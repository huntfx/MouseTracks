from dataclasses import dataclass

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
    resized = QtCore.Signal(QtCore.QSize)

    def __init__(self, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent)
        self.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)
        self.setMinimumSize(1, 1)
        self.setPixmap(QtGui.QPixmap())

    def pixmapSize(self) -> QtCore.QSize:
        """Get the size of the image."""
        return self._pixmap.size()

    def setPixmap(self, pixmap: QtGui.QPixmap | QtGui.QImage) -> None:
        """Set a new pixmap or image."""
        if isinstance(pixmap, QtGui.QPixmap):
            self._pixmap = pixmap
            self._image = pixmap.toImage()
        else:
            self._image = pixmap
            self._pixmap.convertFromImage(pixmap)
        super().setPixmap(self._scaledPixmap())

    def clearPixmap(self) -> None:
        """Clear the pixmap without setting a new one.
        This should only be used to unload from memory.
        """
        self._pixmap = QtGui.QPixmap()
        self._image = self._pixmap.toImage()
        super().setPixmap(self._pixmap)

    def _scaledPixmap(self, aspectRatio=QtCore.Qt.AspectRatioMode.KeepAspectRatio) -> QtGui.QPixmap:
        """Scale the pixmap to the correct size."""
        if self._pixmap.isNull():
            return self._pixmap
        if self.size() == self._pixmap.size():
            return self._pixmap
        return self._pixmap.scaled(self.size(), aspectRatio, QtCore.Qt.TransformationMode.SmoothTransformation)

    def freezeScale(self) -> bool:
        """Set the current size to the scaled size.
        Returns if the size has changed.
        """
        size = self._pixmap.size()
        scaled = self._scaledPixmap()
        if size == scaled.size():
            return False

        self.setPixmap(scaled)
        return True

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

    def resizeEvent(self, event: QtGui.QResizeEvent):
        """Update the pixmap while resizing."""
        self.resized.emit(event.size())
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


class Splitter(QtWidgets.QSplitter):
    """Add extra methods to the QSplitter."""

    def isHandleVisible(self) -> bool:
        """Determine if any handle is visible."""
        for child in self.children():
            if isinstance(child, QtWidgets.QSplitterHandle) and child.isVisible():
                return True
        return False
