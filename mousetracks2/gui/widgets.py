import time
from dataclasses import dataclass

from PySide6 import QtCore, QtGui, QtWidgets


@dataclass
class Pixel:
    """Pixel to update."""

    pixel: QtCore.QPoint
    colour: QtGui.QColor

    def draw(self, image: QtGui.QImage) -> None:
        """Draw the pixel on an image."""
        image.setPixelColor(self.pixel, self.colour)


class OverlayLabel(QtWidgets.QLabel):
    """A semi-transparent overlay label for displaying messages."""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("""
            background-color: rgba(0, 0, 0, 150);
            color: white;
            font: bold 16px;
            border-radius: 1px;
            padding: 6px;
        """)

    def show_message(self, text: str) -> None:
        """Show the overlay with a message."""
        self.setText(text)
        self.adjustSize()
        self.show()

    def hide_message(self) -> None:
        """Hide the overlay."""
        self.hide()


class PlaybackOverlay(QtWidgets.QWidget):
    """An overlay widget that displays a play or pause icon."""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_OpaquePaintEvent, False)
        self.playback_state = True
        self.overlay_size = 1.0

    def _mul(self, value: int) -> int:
        """Multiply a value with the overlay size."""
        return round(value * self.overlay_size)

    @property
    def playback_state(self) -> bool:
        """Get the current overlay playback state."""
        return self.playing

    @playback_state.setter
    def playback_state(self, playing: bool) -> None:
        """Set whether the overlay should display play or pause."""
        self.playing = playing
        self.update()

    @property
    def overlay_size(self) -> float:
        """Get the overlay size."""
        return self._overlay_size

    @overlay_size.setter
    def overlay_size(self, size: float) -> None:
        """Set the overlay size."""
        self._overlay_size = size

        self.setFixedSize(round(50 * size), round(50 * size))
        self._overlay_play = QtGui.QPolygon([
            QtCore.QPoint(self._mul(10), self._mul(5)),
            QtCore.QPoint(self._mul(40), self._mul(25)),
            QtCore.QPoint(self._mul(10), self._mul(45)),
        ])
        self._overlay_pause_l = QtCore.QRect(self._mul(10), self._mul(5), self._mul(10), self._mul(40))
        self._overlay_pause_r = QtCore.QRect(self._mul(30), self._mul(5), self._mul(10), self._mul(40))

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        """Draw the play or pause symbol."""
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)

        # Draw two orange pause bars
        if self.playback_state:
            painter.setBrush(QtGui.QColor(255, 140, 0, 164))
            painter.setPen(QtCore.Qt.PenStyle.NoPen)
            painter.drawRect(self._overlay_pause_l)
            painter.drawRect(self._overlay_pause_r)

        # Draw a green play triangle when paused
        else:
            painter.setBrush(QtGui.QColor(0, 200, 0, 164))
            painter.setPen(QtCore.Qt.PenStyle.NoPen)
            painter.drawPolygon(self._overlay_play)

        painter.end()


class ResizableImage(QtWidgets.QLabel):
    """QLabel used to display a resizable image."""

    clicked = QtCore.Signal(bool)
    doubleClicked = QtCore.Signal()
    resized = QtCore.Signal(QtCore.QSize)

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        self._renderingTextVisible = False
        super().__init__(parent)
        self.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)
        self.setMinimumSize(1, 1)
        self.setMouseTracking(True)
        self.set_pixmap(QtGui.QPixmap())

        self.text_overlay = OverlayLabel(self)
        self.text_overlay.hide()
        self.playback_overlay = PlaybackOverlay(self)
        self.playback_overlay.hide()

        self.move_timer = QtCore.QTimer(self)
        self.move_timer.setSingleShot(True)
        self.move_timer.timeout.connect(self.playback_overlay.hide)

    def pixmap_size(self) -> QtCore.QSize:
        """Get the size of the image."""
        return self._pixmap.size()

    def set_pixmap(self, pixmap: QtGui.QPixmap | QtGui.QImage) -> None:
        """Set a new pixmap or image."""
        if isinstance(pixmap, QtGui.QPixmap):
            self._pixmap = pixmap
            self._image = pixmap.toImage()
        else:
            self._image = pixmap
            self._pixmap.convertFromImage(pixmap)
        self._renderingTextVisible = False
        self.setPixmap(self._scaled_pixmap())

    def clear_pixmap(self) -> None:
        """Clear the pixmap without setting a new one.
        This should only be used to unload from memory.
        """
        self._pixmap = QtGui.QPixmap()
        self._image = self._pixmap.toImage()
        self.setPixmap(self._pixmap)

    def _scaled_pixmap(self, aspect_mode: QtCore.Qt.AspectRatioMode = QtCore.Qt.AspectRatioMode.KeepAspectRatio) -> QtGui.QPixmap:
        """Scale the pixmap to the correct size."""
        if self._pixmap.isNull():
            return self._pixmap
        if self.size() == self._pixmap.size():
            return self._pixmap
        return self._pixmap.scaled(self.size(), aspect_mode, QtCore.Qt.TransformationMode.SmoothTransformation)

    def freeze_scale(self, aspect_mode: QtCore.Qt.AspectRatioMode = QtCore.Qt.AspectRatioMode.KeepAspectRatio) -> bool:
        """Set the current size to the scaled size.
        Returns if the size has changed.
        """
        size = self._pixmap.size()
        scaled = self._scaled_pixmap(aspect_mode)
        if size == scaled.size():
            return False

        self.set_pixmap(scaled)
        return True

    def update_pixels(self, *pixels: Pixel) -> None:
        """Update pixels on the image.
        It is recommended to batch the updates when possible.
        """
        if not pixels:
            return

        # Write each pixel to the image
        for pixel in pixels:
            pixel.draw(self._image)

        # Update the pixmap
        self._pixmap.convertFromImage(self._image)
        self.setPixmap(self._scaled_pixmap())

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        """Update the pixmap while resizing."""
        self.resized.emit(event.size())
        super().resizeEvent(event)
        self.set_pixmap(self._pixmap)
        self.update_text_overlay()

        self.playback_overlay.overlay_size = min(event.size().width(), event.size().height()) / 300
        self.update_playback_overlay()

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        """Emit a signal when the label is clicked."""
        self.playback_overlay.playback_state = not self.playback_overlay.playback_state
        self.clicked.emit(self.playback_overlay.playback_state)
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event: QtGui.QMouseEvent) -> None:
        """Emit a signal when the label is double clicked."""
        self.doubleClicked.emit()
        super().mouseDoubleClickEvent(event)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        """Show playback overlay on mouse move.
        A timer is triggered to hide it after 2 seconds.
        """
        self.playback_overlay.show()
        self.update_playback_overlay()
        self.move_timer.start(1500)
        super().mouseMoveEvent(event)

    def leaveEvent(self, event: QtCore.QEvent) -> None:
        """Hide playback overlay on mouse leave."""
        self.playback_overlay.hide()

    def show_rendering_text(self, text: str = 'Preview render out of date, waiting for response...') -> None:
        """Show the overlay with the rendering message."""
        self.text_overlay.show_message(text)
        self.update_text_overlay()

    def hide_rendering_text(self) -> None:
        """Hide the overlay message."""
        self.text_overlay.hide_message()

    def update_text_overlay(self) -> None:
        """Update overlay position."""
        if self.text_overlay.isVisible():
            self.text_overlay.move((self.width() - self.text_overlay.width()) // 2,
                                   (self.height() - self.text_overlay.height()) // 2)

    def update_playback_overlay(self) -> None:
        """Update overlay position."""
        if self.playback_overlay.isVisible():
            self.playback_overlay.move((self.width() - self.playback_overlay.width()) // 2,
                                       (self.height() - self.playback_overlay.height()) // 2)


class Splitter(QtWidgets.QSplitter):
    """Add extra methods to the QSplitter."""

    def is_handle_visible(self) -> bool:
        """Determine if any handle is visible."""
        for child in self.children():
            if isinstance(child, QtWidgets.QSplitterHandle) and child.isVisible():
                return True
        return False


class AutoCloseMessageBox(QtWidgets.QMessageBox):
    def exec_with_timeout(self, action: str, timeout: float, accuracy: int = 1) -> int:
        """Sets a timeout before accepting the message.
        `setInformativeText` is used to display the remaining time.
        """
        parent = self.parent()
        if parent is None:
            raise RuntimeError('parent required')
        target_timeout = time.time() + timeout

        def update_message() -> None:
            """Updates the countdown message and auto-saves if time runs out."""
            remaining_timeout = round(target_timeout - time.time(), accuracy)
            if remaining_timeout > 0:
                self.setInformativeText(f'{action} in {remaining_timeout} seconds...')
            else:
                timer.stop()
                self.accept()
        update_message()

        # Use a QTimer to update the countdown
        timer = QtCore.QTimer(parent)
        timer.timeout.connect(update_message)
        timer.start(10 ** (3 - accuracy))

        return self.exec()
