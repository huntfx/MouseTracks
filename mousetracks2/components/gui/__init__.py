import os
import sys
import queue
import math
import multiprocessing

import numpy as np
from PIL import Image
from PySide6 import QtCore, QtWidgets, QtGui

from .. import ipc
from ...utils.math import calculate_line, calculate_distance
from ...utils.win import cursor_position, monitor_locations


class QueueWorker(QtCore.QObject):
    """Worker for polling the queue in a background thread."""
    message_received = QtCore.Signal(ipc.Message)

    def __init__(self, queue: multiprocessing.Queue) -> None:
        super().__init__()
        self.queue = queue
        self.running = True

    def run(self) -> None:
        """Continuously poll the queue for messages."""
        while True:
            try:
                message = self.queue.get(timeout=1)
            except queue.Empty:
                if self.running:
                    continue
                break
            self.message_received.emit(message)

    def stop(self) -> None:
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

    def __init__(self, q_send: multiprocessing.Queue, q_receive: multiprocessing.Queue) -> None:
        super().__init__()
        self.q_send = q_send
        self.q_receive = q_receive

        self.pause_redraw = False
        self.redraw_queue: list[tuple[int, int, QtGui.QColor]] = []

        self.mouse_distance = 0.0
        self.mouse_speed = 0.0
        self.mouse_position = cursor_position()
        self.mouse_move_tick = 0
        self.mouse_move_count = 0
        self.monitor_data = monitor_locations()
        self.render_type = ipc.RenderType.Time

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
        render = QtWidgets.QPushButton('Render')
        render.clicked.connect(self.render)
        layout.addWidget(render)

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

        self.thumbtype = QtWidgets.QComboBox()
        self.thumbtype.addItem('Time', ipc.RenderType.Time)
        self.thumbtype.addItem('Time (since pause)', ipc.RenderType.TimeSincePause)
        self.thumbtype.addItem('Speed', ipc.RenderType.Speed)
        self.thumbtype.currentIndexChanged.connect(self.render_type_changed)
        layout.addWidget(self.thumbtype)

        # Create a label to display the pixmap
        self.image_label = QtWidgets.QLabel()
        #self.image_label.setFixedSize(width, height)
        layout.addWidget(self.image_label)
        # Create a QPixmap and QImage
        self.pixmap = QtGui.QPixmap(360, 240)
        self.pixmap.fill(QtCore.Qt.GlobalColor.black)
        self.image_label.setPixmap(self.pixmap)
        self.image = self.pixmap.toImage()
        self.update_pixel.connect(self.update_pixmap_pixel)

        self.setCentralWidget(QtWidgets.QWidget())
        self.centralWidget().setLayout(layout)

        # Start queue worker
        self.queue_thread = QtCore.QThread()
        self.queue_worker = QueueWorker(q_receive)
        self.queue_worker.moveToThread(self.queue_thread)

        # Connect signals and slots
        self.queue_worker.message_received.connect(self.process_message)
        self.queue_thread.started.connect(self.queue_worker.run)
        self.queue_thread.finished.connect(self.queue_worker.deleteLater)

        # Start the thread
        self.queue_thread.start()

    @QtCore.Slot(int)
    def render_type_changed(self, idx: int) -> None:
        """Change the thumbnail type and trigger a redraw."""
        self.render_type = self.thumbtype.itemData(idx)
        self.request_thumbnail(force=True)

    def _monitor_offset(self, pixel: tuple[int, int]) -> tuple[tuple[int, int], tuple[int, int]]:
        """Detect which monitor the pixel is on."""
        for x1, y1, x2, y2 in self.monitor_data:
            if x1 <= pixel[0] < x2 and y1 <= pixel[1] < y2:
                return ((x2 - x1, y2 - y1), (x1, y1))
        raise ValueError(f'coordinate {pixel} not in monitors')

    def request_thumbnail(self, force: bool = False) -> None:
        """Send a request to draw a thumbnail.
        This will start pooling mouse move data to be redrawn after.
        """
        # If already redrawing then prevent building up commands
        if self.pause_redraw and not force:
            return
        self.pause_redraw = True
        self.q_send.put(ipc.RenderRequest(self.render_type, self.pixmap.width(), self.pixmap.height(), False))

    def render(self) -> None:
        """Send a render request."""
        self.q_send.put(ipc.RenderRequest(self.render_type, 2560, 1440, True))

    @QtCore.Slot(ipc.Message)
    def process_message(self, message: ipc.Message) -> None:
        match message:
            # When monitors change, store the new data
            case ipc.MonitorsChanged():
                self.monitor_data = message.data

            # Save a render
            case ipc.Render(data=array, thumbnail=False):
                dialog = QtWidgets.QFileDialog()
                dialog.setAcceptMode(QtWidgets.QFileDialog.AcceptMode.AcceptSave)
                dialog.setNameFilters(['PNG Files (*.png)", "JPEG Files (*.jpg *.jpeg)'])
                dialog.setDefaultSuffix('png')
                file_path, accept = dialog.getSaveFileName(None, 'Save Image', '', 'Image Files (*.png *.jpg)')

                if accept:
                    im = Image.fromarray(array)
                    im.resize((2560, 1440), Image.Resampling.LANCZOS)
                    im.save(file_path)
                    os.startfile(file_path)

            # Draw the new pixmap
            case ipc.Render(data=array, thumbnail=True):
                # Create a QImage from the array
                height, width, channels = array.shape
                if channels == 1:
                    image_format = QtGui.QImage.Format.Format_Grayscale8
                elif channels == 3:
                    image_format = QtGui.QImage.Format.Format_RGB888
                else:
                    raise NotImplementedError(channels)
                image = QtGui.QImage(array.data, width, height, image_format)

                # Scale the QImage to fit the pixmap size
                scaled_image = image.scaled(width, height, QtCore.Qt.AspectRatioMode.KeepAspectRatio)

                # Draw the QImage onto the QPixmap
                painter = QtGui.QPainter(self.pixmap)
                painter.drawImage(0, 0, scaled_image)
                painter.end()
                self.image_label.setPixmap(self.pixmap)
                self.image = self.pixmap.toImage()

                self.pause_redraw = False

            # When the mouse moves, update stats and draw it
            # The drawing is an approximation and not a render
            case ipc.MouseMove():
                pixels = [message.position]
                if self.mouse_position is not None and message.tick == self.mouse_move_tick + 1:
                    # Calculate basic data
                    distance_to_previous = calculate_distance(message.position, self.mouse_position)
                    self.mouse_speed = distance_to_previous
                    self.mouse_distance += distance_to_previous

                    # Get all the pixels between the two points
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
                        self.update_pixmap_pixel(int(x), int(y), QtCore.Qt.GlobalColor.white)
                        seen.add((x, y))

                # Update the widgets
                self.distance.setText(str(int(self.mouse_distance)))
                self.speed.setText(str(int(self.mouse_speed)))

                # Update the saved data
                self.mouse_move_count += 1
                self.mouse_position = message.position
                self.mouse_move_tick = message.tick

                # Trigger a GUI update
                if self.mouse_move_count:
                    update_smoothness = 4
                    match self.render_type:
                        # This does it every 10, 20, ..., 90, 100, 200, ..., 900, 1000, 2000, etc
                        case ipc.RenderType.Time:
                            update_frequency = min(20000, 10 ** int(math.log10(max(10, self.mouse_move_count))))
                        # With speed it must be constant, doesn't work as well live
                        case ipc.RenderType.Speed | ipc.RenderType.TimeSincePause:
                            update_frequency = 50
                        case _:
                            raise NotImplementedError(self.render_type)
                    if not self.mouse_move_count % (update_frequency // update_smoothness):
                        self.request_thumbnail()

    @QtCore.Slot()
    def startTracking(self) -> None:
        """Start/unpause the script."""
        self.q_send.put(ipc.TrackingState(ipc.TrackingState.State.Start))

    @QtCore.Slot()
    def pauseTracking(self) -> None:
        """Pause/unpause the script."""
        self.q_send.put(ipc.TrackingState(ipc.TrackingState.State.Pause))

        # Special case to redraw thumbnail
        if self.thumbtype.currentData() == ipc.RenderType.TimeSincePause:
            self.request_thumbnail()

    @QtCore.Slot()
    def stopTracking(self) -> None:
        """Stop the script."""
        self.q_send.put(ipc.TrackingState(ipc.TrackingState.State.Stop))

    @QtCore.Slot()
    def raiseTracking(self) -> None:
        """Send a command to raise an exception.
        For testing purposes only.
        """
        self.q_send.put(ipc.DebugRaiseError(ipc.Target.Tracking))

    @QtCore.Slot()
    def raiseProcessing(self) -> None:
        """Send a command to raise an exception.
        For testing purposes only.
        """
        self.q_send.put(ipc.DebugRaiseError(ipc.Target.Processing))

    @QtCore.Slot()
    def raiseHub(self) -> None:
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
    def update_pixmap_pixel(self, x: int, y: int, colour: QtGui.QColor) -> None:
        """Update a specific pixel in the QImage and refresh the display."""
        if self.render_type in (ipc.RenderType.Time, ipc.RenderType.TimeSincePause):
            self.image.setPixelColor(x, y, colour)
            self.pixmap.convertFromImage(self.image)
            self.image_label.setPixmap(self.pixmap)

        # Queue commands if redrawing is paused
        # This allows them to be resubmitted
        if self.pause_redraw:
            self.redraw_queue.append((x, y, colour))
        elif self.redraw_queue:
            redraw_queue, self.redraw_queue = self.redraw_queue, []
            for x, y, colour in redraw_queue:
                self.update_pixmap_pixel(x, y, colour)


def run(q_send: multiprocessing.Queue, q_receive: multiprocessing.Queue) -> None:
    app = QtWidgets.QApplication(sys.argv)
    m = MainWindow(q_send, q_receive)
    m.show()
    app.exec()
