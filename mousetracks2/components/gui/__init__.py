from enum import Enum, auto
from PySide6 import QtCore, QtWidgets, QtGui
from threading import Thread
import sys
import queue
import math
import numpy as np
from .. import ipc
from ...utils.math import calculate_line, calculate_distance
from ...utils.win import cursor_position, monitor_locations

try:
    from scipy import ndimage
except ImportError:
    ndimage = None


def max_pool_downscale(array: np.ndarray, target_width: int, target_height: int) -> np.ndarray:
    """Downscale the array using max pooling with edge correction.

    All credit goes to ChatGPT here. With scipy it's a tiny bit faster
    but I've left both ways for the time being.
    """
    input_height, input_width = array.shape

    # Compute the pooling size
    block_width = input_width / target_width
    block_height = input_height / target_height

    # Use scipy
    if ndimage is not None:
        # Apply maximum filter with block size
        pooled_full = ndimage.maximum_filter(array, size=(int(math.ceil(block_height)), int(math.ceil(block_width))))

        # Downsample by slicing
        stride_y = input_height / target_height
        stride_x = input_width / target_width

        indices_y = (np.arange(target_height) * stride_y).astype(int)
        indices_x = (np.arange(target_width) * stride_x).astype(int)

        return np.ascontiguousarray(pooled_full[indices_y][:, indices_x])

    # Create an output array
    pooled = np.zeros((target_height, target_width), dtype=array.dtype)

    for y in range(target_height - 1):
        for x in range(target_width - 1):
            # Compute the bounds of the current block
            x_start = int(x * block_width)
            x_end = min(int((x + 1) * block_width), input_width)
            y_start = int(y * block_height)
            y_end = min(int((y + 1) * block_height), input_height)

            # Pool the maximum value from the block
            pooled[y, x] = array[y_start:y_end, x_start:x_end].max()

    return pooled


class QueueWorker(QtCore.QObject):
    """Worker for polling the queue in a background thread."""
    message_received = QtCore.Signal(ipc.Message)

    def __init__(self, queue):
        super().__init__()
        self.queue = queue
        self.running = True

    def run(self):
        """Continuously poll the queue for messages."""
        while True:
            try:
                message = self.queue.get(timeout=1)
            except queue.Empty:
                if self.running:
                    continue
                break
            self.message_received.emit(message)

    def stop(self):
        """Stop the worker."""
        self.running = False


class MainWindow(QtWidgets.QMainWindow):
    """Window used to wrap the main program.
    This does not directly do any tracking, it is just meant as an
    interface to the script itself.

    Communication:
        Every time an option is chosen in the GUI, a corresponding
        command is added to the queue. The thread will read the queue
        in a "first in first out" method. If the thread is "paused",
        then it will still read all commands, but it may ignore some.
        The queue contains instances of `GUICommand`.

        The thread in return will send data back by using the
        `receiveFromThread` method. Instead of using a queue, the GUI
        will instantly execute the command. This uses instances of
        `ThreadEvent`.
    """
    update_pixel = QtCore.Signal(int, int, QtGui.QColor)

    def __init__(self, q_send, q_receive, **kwargs):
        super().__init__(**kwargs)
        self.q_send = q_send
        self.q_receive = q_receive

        self.pause_redraw = False
        self.redraw_queue: list[tuple[int, int, QtGui.QColor]] = []

        self.mouse_distance = 0
        self.mouse_speed = 0
        self.mouse_position = cursor_position()
        self.mouse_move_tick = 0
        self.monitor_data = monitor_locations()
        self.previous_monitor = None

        # Setup layout
        # This is a design meant for debugging purposes
        layout = QtWidgets.QVBoxLayout()
        start = QtWidgets.QPushButton('Start')
        start.clicked.connect(self.startTracking)
        layout.addWidget(start)
        start = QtWidgets.QPushButton('Stop')
        start.clicked.connect(self.stopTracking)
        layout.addWidget(start)
        pause = QtWidgets.QPushButton('Pause')
        pause.clicked.connect(self.pauseTracking)
        layout.addWidget(pause)
        crash = QtWidgets.QPushButton('Raise Exception (tracking)')
        crash.clicked.connect(self.raiseTracking)
        layout.addWidget(crash)
        crash = QtWidgets.QPushButton('Raise Exception (processing)')
        crash.clicked.connect(self.raiseProcessing)
        layout.addWidget(crash)
        crash = QtWidgets.QPushButton('Raise Exception (hub)')
        crash.clicked.connect(self.raiseHub)
        layout.addWidget(crash)

        horizontal = QtWidgets.QHBoxLayout()
        horizontal.addWidget(QtWidgets.QLabel('Current Status:'))
        self.status = QtWidgets.QLabel()
        horizontal.addWidget(self.status)
        layout.addLayout(horizontal)

        horizontal = QtWidgets.QHBoxLayout()
        horizontal.addWidget(QtWidgets.QLabel('Total Mouse Distance:'))
        self.distance = QtWidgets.QLabel('0.0')
        horizontal.addWidget(self.distance)
        layout.addLayout(horizontal)

        horizontal = QtWidgets.QHBoxLayout()
        horizontal.addWidget(QtWidgets.QLabel('Current Mouse Speed:'))
        self.speed = QtWidgets.QLabel('0.0')
        horizontal.addWidget(self.speed)
        layout.addLayout(horizontal)

        # Create a label to display the pixmap
        self.image_label = QtWidgets.QLabel()
        #self.image_label.setFixedSize(width, height)
        layout.addWidget(self.image_label)
        # Create a QPixmap and QImage
        self.pixmap = QtGui.QPixmap(360, 240)
        self.pixmap.fill(QtCore.Qt.black)
        self.image_label.setPixmap(self.pixmap)
        self.image = self.pixmap.toImage()
        self.update_pixel.connect(self.update_pixmap_pixel)

        self.setCentralWidget(QtWidgets.QWidget())
        self.centralWidget().setLayout(layout)

        # Window setup
        self.setState('stopped')

        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(1000)

        # Start queue worker
        self.queue_thread = QtCore.QThread()
        self.queue_worker = QueueWorker(q_receive)
        self.queue_worker.moveToThread(self.queue_thread)

        # Connect signals and slots
        self.queue_worker.message_received.connect(self.process_message)
        self.queue_thread.started.connect(self.queue_worker.run)
        self.queue_thread.finished.connect(self.queue_worker.deleteLater)
        self.timer.timeout.connect(self.request_redraw)

        # Start the thread
        self.queue_thread.start()
        self.timer.start()

    def closeEvent(self, event):
        """Safely close the thread."""
        if self.thread():
            self.stopTracking()
        return super().closeEvent(event)

    def state(self):
        """Get the current script state."""
        return self._state

    def setState(self, state):
        """Set the new thread state.
        This is for display purposes only.

        Parameters:
            state (ThreadState): State of the thread.
                It can be Running, Paused or Stopped.
        """
        self._state = state
        self.status.setText(state)

    def _monitor_offset(self, pixel: tuple[int, int]) -> tuple[tuple[int, int], tuple[int, int]]:
        """Detect which monitor the pixel is on."""
        for x1, y1, x2, y2 in self.monitor_data:
            if x1 <= pixel[0] < x2 and y1 <= pixel[1] < y2:
                return ((x2 - x1, y2 - y1), (x1, y1))

    def request_redraw(self):
        self.pause_redraw = True
        self.q_send.put(ipc.GuiArrayRequest())

    @QtCore.Slot(ipc.Message)
    def process_message(self, message: ipc.Message):
        match message:
            # When monitors change, store the new data
            case ipc.MonitorsChanged():
                self.monitor_data = message.data

            # Draw the new pixmap
            case ipc.GuiArrayReply():
                width, height = self.pixmap.width(), self.pixmap.height()
                array = max_pool_downscale(message.array, width, height)

                # Normalise values from 0 - 255
                if np.any(array):
                    array = (255 * array / np.max(array))

                # Create a QImage from the array
                height, width = array.shape
                image = QtGui.QImage(array.astype(np.uint8).data, width, height, QtGui.QImage.Format_Grayscale8)

                # Scale the QImage to fit the pixmap size
                scaled_image = image.scaled(width, height, QtCore.Qt.KeepAspectRatio)

                # Draw the QImage onto the QPixmap
                painter = QtGui.QPainter(self.pixmap)
                painter.drawImage(0, 0, scaled_image)
                painter.end()
                self.image_label.setPixmap(self.pixmap)
                self.image = self.pixmap.toImage()

                # Resume drawing
                self.pause_redraw = False

            # When the mouse moves, update stats and draw it
            # The drawing is an approximation and not a render
            case ipc.MouseMove():
                is_moving = message.tick == self.mouse_move_tick + 1

                # Calculate basic data
                distance_to_previous = calculate_distance(message.position, self.mouse_position)
                if is_moving:
                    self.mouse_speed = distance_to_previous
                self.mouse_distance += distance_to_previous

                # Get all the pixels between the two points
                # Unlike the processing component, this skips the first
                # point as there are no colour gradients to see
                pixels = [message.position]
                if is_moving and self.mouse_position != message.position:
                    pixels.extend(calculate_line(message.position, self.mouse_position))

                seen = set()
                for pixel in pixels:
                    # Refresh data per pixel
                    # This could be done only when the cursor changes
                    # monitor, but it's not computationally heavy
                    current_monitor, offset = self._monitor_offset(pixel)
                    width_multiplier = self.image.width() / current_monitor[0]
                    height_multiplier = self.image.height() / current_monitor[1]

                    # Downscale the pixel to match the pixmap
                    x = int((pixel[0] - offset[0]) * width_multiplier)
                    y = int((pixel[1] - offset[1]) * height_multiplier)

                    # Send (unique) pixels to be drawn
                    if (x, y) not in seen:
                        self.update_pixel.emit(int(x), int(y), QtCore.Qt.white)
                        seen.add((x, y))

                # Update the widgets
                self.distance.setText(str(int(self.mouse_distance)))
                self.speed.setText(str(int(self.mouse_speed)))

                # Update the saved data
                self.mouse_position = message.position
                self.mouse_move_tick = message.tick
                self.previous_monitor = (current_monitor, offset)

    @QtCore.Slot()
    def startTracking(self):
        """Start/unpause the script."""
        self.q_send.put(ipc.TrackingState(ipc.TrackingState.State.Start))

    @QtCore.Slot()
    def pauseTracking(self):
        """Pause/unpause the script."""
        self.q_send.put(ipc.TrackingState(ipc.TrackingState.State.Pause))

    @QtCore.Slot()
    def stopTracking(self):
        """Stop the script."""
        self.q_send.put(ipc.TrackingState(ipc.TrackingState.State.Stop))

    @QtCore.Slot()
    def raiseTracking(self):
        """Send a command to raise an exception.
        For testing purposes only.
        """
        self.q_send.put(ipc.DebugRaiseError(ipc.Target.Tracking))

    @QtCore.Slot()
    def raiseProcessing(self):
        """Send a command to raise an exception.
        For testing purposes only.
        """
        self.q_send.put(ipc.DebugRaiseError(ipc.Target.Processing))

    @QtCore.Slot()
    def raiseHub(self):
        """Send a command to raise an exception.
        For testing purposes only.
        """
        self.q_send.put(ipc.DebugRaiseError(ipc.Target.Hub))

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        """Send a signal that the GUI has closed."""
        self.queue_worker.stop()
        self.q_send.put(ipc.Exit())
        self.queue_thread.quit()
        self.queue_thread.wait()
        super().closeEvent(event)

    @QtCore.Slot(int, int, QtGui.QColor)
    def update_pixmap_pixel(self, x: int, y: int, colour: QtGui.QColor):
        """Update a specific pixel in the QImage and refresh the display."""
        if self.pause_redraw:
            self.redraw_queue.append((x, y, colour))

        self.image.setPixelColor(x, y, colour)
        self.pixmap.convertFromImage(self.image)
        self.image_label.setPixmap(self.pixmap)

        if not self.pause_redraw and self.redraw_queue:
            redraw_queue = tuple(self.redraw_queue)
            self.redraw_queue.clear()
            for x, y, colour in redraw_queue:
                self.update_pixmap_pixel(x, y, colour)

def run(q_send, q_receive):
    app = QtWidgets.QApplication(sys.argv)
    m = MainWindow(q_send, q_receive)
    m.show()
    app.exec()
