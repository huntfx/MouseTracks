import os
import sys
import queue
import math
import multiprocessing
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
from PIL import Image
from PySide6 import QtCore, QtWidgets, QtGui

from mousetracks.image import colours
from .. import ipc
from ...utils.math import calculate_line, calculate_distance, calculate_pixel_offset
from ...utils.win import cursor_position, monitor_locations


COMPRESSION_FACTOR = 1.1

COMPRESSION_THRESHOLD = 425000  # Max: 2 ** 64 - 1


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


@dataclass
class MapData:
    position: Optional[tuple[int, int]] = field(default_factory=cursor_position)
    distance: float = field(default=0.0)
    move_count: int = field(default=0)
    move_tick: int = field(default=0)


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
        self.pause_colour_change = False
        self.redraw_queue: list[tuple[int, int, QtGui.QColor]] = []

        # Setup layout
        # This is a design meant for debugging purposes
        layout = QtWidgets.QVBoxLayout()
        start = QtWidgets.QPushButton('Start')
        layout.addWidget(start)
        stop = QtWidgets.QPushButton('Stop')
        layout.addWidget(stop)
        pause = QtWidgets.QPushButton('Pause')
        layout.addWidget(pause)
        crasht = QtWidgets.QPushButton('Raise Exception (tracking)')
        layout.addWidget(crasht)
        crashp = QtWidgets.QPushButton('Raise Exception (processing)')
        layout.addWidget(crashp)
        crashh = QtWidgets.QPushButton('Raise Exception (hub)')
        layout.addWidget(crashh)

        horizontal = QtWidgets.QHBoxLayout()
        render = QtWidgets.QPushButton('Render')
        horizontal.addWidget(render)
        horizontal.addWidget(QtWidgets.QLabel('Sampling'))
        self.sampling = QtWidgets.QDoubleSpinBox()
        self.sampling.setMinimum(1)
        self.sampling.setValue(4)
        self.sampling.setMaximum(8)
        horizontal.addWidget(self.sampling)
        layout.addLayout(horizontal)

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

        self.application_input = QtWidgets.QComboBox()
        self.application_input.addItem('Current Application')
        self.application_input.addItem('Main')
        layout.addWidget(self.application_input)

        self.render_type_input = QtWidgets.QComboBox()
        self.render_type_input.addItem('Time', ipc.RenderType.Time)
        self.render_type_input.addItem('Time (since pause)', ipc.RenderType.TimeSincePause)
        self.render_type_input.addItem('Time (heatmap)', ipc.RenderType.TimeHeatmap)
        self.render_type_input.addItem('Speed', ipc.RenderType.Speed)
        self.render_type_input.addItem('Clicks', ipc.RenderType.SingleClick)
        self.render_type_input.addItem('Double Clicks', ipc.RenderType.DoubleClick)
        self.render_type_input.addItem('Held Clicks', ipc.RenderType.HeldClick)
        self.render_type_input.addItem('Left Thumbstick', ipc.RenderType.Thumbstick_L)
        self.render_type_input.addItem('Right Thumbstick', ipc.RenderType.Thumbstick_R)
        self.render_type_input.addItem('Left Thumbstick (heatmap)', ipc.RenderType.Thumbstick_L_Heatmap)
        self.render_type_input.addItem('Right Thumbstick (heatmap)', ipc.RenderType.Thumbstick_R_Heatmap)
        self.render_type_input.addItem('Left Thumbstick (speed)', ipc.RenderType.Thumbstick_L_SPEED)
        self.render_type_input.addItem('Right Thumbstick (speed)', ipc.RenderType.Thumbstick_R_SPEED)
        self.render_type_input.addItem('Triggers', ipc.RenderType.Trigger)
        self.render_type_input.addItem('Triggers (heatmap)', ipc.RenderType.TriggerHeatmap)
        layout.addWidget(self.render_type_input)

        self.render_colour_input = QtWidgets.QComboBox()
        layout.addWidget(self.render_colour_input)

        # Create a label to display the pixmap
        self.image_label = QtWidgets.QLabel()
        #self.image_label.setFixedSize(width, height)
        layout.addWidget(self.image_label)
        # Create a QPixmap and QImage
        self.pixmap = QtGui.QPixmap(360, 240)
        self.pixmap.fill(QtCore.Qt.GlobalColor.black)
        self.image_label.setPixmap(self.pixmap)
        self.image = self.pixmap.toImage()

        self.setCentralWidget(QtWidgets.QWidget())
        self.centralWidget().setLayout(layout)

        self.cursor_data = MapData(cursor_position())
        self.thumbstick_l_data = MapData((0, 0))
        self.thumbstick_r_data = MapData((0, 0))
        self.trigger_data = MapData((0, 0))

        self.mouse_click_count = 0
        self.mouse_held_count = 0
        self.monitor_data = monitor_locations()
        self.render_type = ipc.RenderType.Time
        self.render_colour = 'BlackToRedToWhite'
        self.tick_current = 0
        self.last_render: tuple[ipc.RenderType, int] = (self.render_type, -1)
        self.current_app: str = 'Main'
        self.current_app_position: Optional[tuple[int, int, int, int]] = None

        # Start queue worker
        self.queue_thread = QtCore.QThread()
        self.queue_worker = QueueWorker(q_receive)
        self.queue_worker.moveToThread(self.queue_thread)

        # Connect signals and slots
        start.clicked.connect(self.startTracking)
        stop.clicked.connect(self.stopTracking)
        pause.clicked.connect(self.pauseTracking)
        crasht.clicked.connect(self.raiseTracking)
        crashp.clicked.connect(self.raiseProcessing)
        crashh.clicked.connect(self.raiseHub)
        render.clicked.connect(self.render)
        self.application_input.currentIndexChanged.connect(self.application_changed)
        self.render_type_input.currentIndexChanged.connect(self.render_type_changed)
        self.render_colour_input.currentIndexChanged.connect(self.render_colour_changed)
        self.queue_worker.message_received.connect(self.process_message)
        self.queue_thread.started.connect(self.queue_worker.run)
        self.queue_thread.finished.connect(self.queue_worker.deleteLater)

        # Start the thread
        self.queue_thread.start()

    @property
    def render_colour(self) -> str:
        """Get the render colour."""
        return self._render_colour

    @render_colour.setter
    def render_colour(self, colour: str) -> None:
        """Set the render colour.
        This will update the current pixel colour too.
        """
        self._render_colour = colour
        self.pixel_colour = colours.calculate_colour_map(colour)[-1]

    @property
    def pixel_colour(self) -> tuple[int, int, int, int]:
        """Get the pixel colour to draw with."""
        return self._pixel_colour

    @pixel_colour.setter
    def pixel_colour(self, colour: tuple[int, int, int, int]):
        """Set the pixel colour to draw with."""
        self._pixel_colour = QtGui.QColor(*colour)

    @property
    def render_type(self) -> ipc.RenderType:
        """Get the render type."""
        return self._render_type

    @render_type.setter
    def render_type(self, render_type: ipc.RenderType):
        """Set the render type.
        This populates the available colour maps.
        """
        self._render_type = render_type

        # Add items to render colour input
        self.pause_colour_change = True
        previous_text = self.render_colour_input.currentData()

        self.render_colour_input.clear()
        self.render_colour_input.addItem('Default', 'BlackToRedToWhite')
        for data in colours.parse_colour_file()['Maps'].values():
            match render_type:
                case (ipc.RenderType.Time| ipc.RenderType.TimeSincePause | ipc.RenderType.Speed
                      | ipc.RenderType.Thumbstick_L | ipc.RenderType.Thumbstick_R
                      | ipc.RenderType.Thumbstick_L_SPEED | ipc.RenderType.Thumbstick_R_SPEED):
                    if data['Type']['tracks']:
                        self.render_colour_input.addItem(data['UpperCase'], data['UpperCase'])
                case (ipc.RenderType.SingleClick | ipc.RenderType.DoubleClick | ipc.RenderType.HeldClick
                      | ipc.RenderType.Thumbstick_L_Heatmap | ipc.RenderType.Thumbstick_R_Heatmap
                      | ipc.RenderType.TriggerHeatmap | ipc.RenderType.TimeHeatmap):
                    if data['Type']['clicks']:
                        self.render_colour_input.addItem(data['UpperCase'], data['UpperCase'])

        # Load previous colour if available, otherwise revert to default
        if previous_text and previous_text != self.render_colour_input.currentData():
            if idx := self.render_colour_input.findData(previous_text) < -1:
                self.render_colour_input.setCurrentIndex(idx)
            self.render_colour = self.render_colour_input.currentData()

        self.pause_colour_change = False

    @QtCore.Slot(int)
    def application_changed(self, idx: int) -> None:
        """Change the render type and trigger a redraw."""
        self.request_thumbnail(force=True)

    @QtCore.Slot(int)
    def render_type_changed(self, idx: int) -> None:
        """Change the render type and trigger a redraw."""
        self.render_type = self.render_type_input.itemData(idx)
        self.request_thumbnail(force=True)

    @QtCore.Slot(int)
    def render_colour_changed(self, idx: int) -> None:
        """Change the render colour and trigger a redraw."""
        if self.pause_colour_change:
            return
        self.render_colour = self.render_colour_input.itemData(idx)
        self.request_thumbnail(force=True)

    def _monitor_offset(self, pixel: tuple[int, int]) -> Optional[tuple[tuple[int, int], tuple[int, int]]]:
        """Detect which monitor the pixel is on."""
        if self.current_app_position is not None:
            monitor_data = [self.current_app_position]
        else:
            monitor_data = self.monitor_data

        for x1, y1, x2, y2 in monitor_data:
            result = calculate_pixel_offset(pixel[0], pixel[1], x1, y1, x2, y2)
            if result is not None:
                return result
        return None

    def request_thumbnail(self, force: bool = False) -> bool:
        """Send a request to draw a thumbnail.
        This will start pooling mouse move data to be redrawn after.
        """
        # If already redrawing then prevent building up commands
        if self.pause_redraw and not force:
            return False
        self.pause_redraw = True
        app = self.application_input.currentText() if self.application_input.currentIndex() else ''
        self.q_send.put(ipc.RenderRequest(self.render_type, self.pixmap.width(), self.pixmap.height(), self.render_colour, 1.0, app))
        return True

    def render(self) -> None:
        """Send a render request."""
        app = self.application_input.currentText() if self.application_input.currentIndex() else ''
        self.q_send.put(ipc.RenderRequest(self.render_type, None, None, self.render_colour, self.sampling.value(), app))

    def thumbnail_render_check(self, update_smoothness: int = 4) -> None:
        """Check if the thumbnail should be re-rendered."""
        match self.render_type:
            # This does it every 10, 20, ..., 90, 100, 200, ..., 900, 1000, 2000, etc
            case ipc.RenderType.Time:
                count = self.cursor_data.move_count
                update_frequency = min(20000, 10 ** int(math.log10(max(10, count))))
            # With speed it must be constant, doesn't work as well live
            case ipc.RenderType.Speed | ipc.RenderType.TimeSincePause | ipc.RenderType.TimeHeatmap:
                update_frequency = 50
                count = self.cursor_data.move_count
            case ipc.RenderType.SingleClick | ipc.RenderType.DoubleClick:
                update_frequency = 1
                count = self.mouse_click_count
            case ipc.RenderType.HeldClick:
                update_frequency = 50
                count = self.mouse_held_count
            case ipc.RenderType.Thumbstick_L:
                count = self.thumbstick_l_data.move_count
                update_frequency = min(20000, 10 ** int(math.log10(max(10, count))))
            case ipc.RenderType.Thumbstick_R:
                count = self.thumbstick_r_data.move_count
                update_frequency = min(20000, 10 ** int(math.log10(max(10, count))))
            case ipc.RenderType.Thumbstick_L_SPEED | ipc.RenderType.Thumbstick_L_Heatmap:
                count = self.thumbstick_l_data.move_count
                update_frequency = 50
            case ipc.RenderType.Thumbstick_R_SPEED | ipc.RenderType.Thumbstick_R_Heatmap:
                count = self.thumbstick_r_data.move_count
                update_frequency = 50
            case ipc.RenderType.Trigger:
                count = self.trigger_data.move_count
                update_frequency = min(20000, 10 ** int(math.log10(max(10, count))))
            case ipc.RenderType.TriggerHeatmap:
                count = self.trigger_data.move_count
                update_frequency = 50
            case _:
                return

        # Don't re-render if there's no data
        if not count:
            return

        # Only render every `update_frequency` ticks
        if count % math.ceil(update_frequency / update_smoothness):
            return

        # Skip repeat renders
        if (self.render_type, count) == self.last_render:
            return

        if self.request_thumbnail():
            self.last_render = (self.render_type, count)

    @QtCore.Slot(ipc.Message)
    def process_message(self, message: ipc.Message) -> None:
        match message:
            case ipc.Tick():
                self.tick_current = message.tick
                self.thumbnail_render_check()

            # When monitors change, store the new data
            case ipc.MonitorsChanged():
                self.monitor_data = message.data

            case ipc.Render():
                height, width, channels = message.array.shape

                target_height = int(height / message.sampling)
                target_width = int(width / message.sampling)

                # Draw the new pixmap
                if (target_width, target_height) == (360, 240):
                    match channels:
                        case 1:
                            image_format = QtGui.QImage.Format.Format_Grayscale8
                        case 3:
                            image_format = QtGui.QImage.Format.Format_RGB888
                        case 4:
                            image_format = QtGui.QImage.Format.Format_RGBA8888
                            self.pixmap.fill(QtCore.Qt.GlobalColor.transparent)
                        case _:
                            raise NotImplementedError(channels)
                    image = QtGui.QImage(message.array.data, width, height, image_format)

                    # Scale the QImage to fit the pixmap size
                    scaled_image = image.scaled(target_width, target_height, QtCore.Qt.AspectRatioMode.KeepAspectRatio)

                    # Draw the QImage onto the QPixmap
                    painter = QtGui.QPainter(self.pixmap)
                    painter.drawImage(0, 0, scaled_image)
                    painter.end()
                    self.image_label.setPixmap(self.pixmap)
                    self.image = self.pixmap.toImage()

                    self.pause_redraw = False

                # Save a render
                else:
                    dialog = QtWidgets.QFileDialog()
                    dialog.setAcceptMode(QtWidgets.QFileDialog.AcceptMode.AcceptSave)
                    dialog.setNameFilters(['PNG Files (*.png)", "JPEG Files (*.jpg *.jpeg)'])
                    dialog.setDefaultSuffix('png')
                    file_path, accept = dialog.getSaveFileName(None, 'Save Image', '', 'Image Files (*.png *.jpg)')

                    if accept:
                        im = Image.fromarray(message.array)
                        im.resize((target_width, target_height), Image.Resampling.LANCZOS)
                        im.save(file_path)
                        os.startfile(file_path)

            case ipc.MouseClick():
                self.mouse_click_count += 1

            case ipc.MouseHeld():
                self.mouse_held_count += 1

            case ipc.MouseMove():
                if self.render_type in (ipc.RenderType.Time, ipc.RenderType.TimeSincePause):
                    self.draw_pixmap_line(message.position, self.cursor_data.position)
                self.update_track_data(self.cursor_data, message.position)
                self.distance.setText(str(int(self.cursor_data.distance)))

            case ipc.ThumbstickMove():
                draw = False
                match message.thumbstick:
                    case ipc.ThumbstickMove.Thumbstick.Left:
                        data = self.thumbstick_l_data
                        draw = self.render_type == ipc.RenderType.Thumbstick_L
                    case ipc.ThumbstickMove.Thumbstick.Right:
                        data = self.thumbstick_r_data
                        draw = self.render_type == ipc.RenderType.Thumbstick_R
                    case _:
                        raise NotImplementedError(message.thumbstick)

                x, y = message.position
                remapped = (int(x * 1024 + 1024), int(-y * 1024 + 1024))
                if draw:
                    self.draw_pixmap_line(remapped, data.position, (2048, 2048))
                self.update_track_data(data, remapped)

            case ipc.TriggerMove():
                position = 4 + int(message.right * 2040), 4 + int(message.left * 2040)
                if self.render_type == ipc.RenderType.Trigger:
                    self.draw_pixmap_line(self.trigger_data.position, position, (2048, 2048))
                self.update_track_data(self.trigger_data, position)

            case ipc.Application():
                for idx in range(1, self.application_input.count()):
                    if self.application_input.itemText(idx) == message.name:
                        break
                else:
                    self.application_input.addItem(message.name)
                self.current_app = message.name
                self.current_app_position = message.position

            case ipc.NoApplication():
                self.current_app = 'Main'
                self.current_app_position = None

    @QtCore.Slot()
    def startTracking(self) -> None:
        """Start/unpause the script."""
        self.cursor_data.position = cursor_position()  # Prevent erroneous line jumps
        self.q_send.put(ipc.TrackingState(ipc.TrackingState.State.Start))

    @QtCore.Slot()
    def pauseTracking(self) -> None:
        """Pause/unpause the script."""
        self.q_send.put(ipc.TrackingState(ipc.TrackingState.State.Pause))

        # Special case to redraw thumbnail
        if self.render_type_input.currentData() == ipc.RenderType.TimeSincePause:
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

        msg = QtWidgets.QMessageBox(self)
        msg.setWindowTitle('Closing MouseTracks Application')
        msg.setText('Do you want to save?')
        msg.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No
                               | QtWidgets.QMessageBox.StandardButton.Cancel)
        match msg.exec_():
            case QtWidgets.QMessageBox.StandardButton.Cancel:
                event.ignore()
                return
            case QtWidgets.QMessageBox.StandardButton.Yes:
                self.q_send.put(ipc.Save())

        self.q_send.put(ipc.Exit())
        self.queue_thread.quit()
        self.queue_thread.wait()
        event.accept()

    def update_track_data(self, data: MapData, position: tuple[int, int]) -> None:
        if data.position is not None and self.tick_current == data.move_tick + 1:
            data.distance += calculate_distance(position, data.position)

        # Update the saved data
        data.move_count += 1
        data.position = position
        data.move_tick = self.tick_current

        # Check if array compression has been done
        if data.move_count > COMPRESSION_THRESHOLD:
            data.move_count = int(data.move_count / COMPRESSION_FACTOR)

    def draw_pixmap_line(self, old_position: Optional[tuple[int, int]], new_position: Optional[tuple[int, int]],
                         force_monitor: Optional[tuple[int, int]] = None):
        """When an object moves, draw it.
        The drawing is an approximation and not a render, and will be
        periodically replaced with an actual render.
        """
        if self.application_input.currentIndex() and self.application_input.currentText() != self.current_app:
            return

        seen = set()
        for pixel in calculate_line(old_position, new_position):
            # Refresh data per pixel
            # This could be done only when the cursor changes
            # monitor, but it's not computationally heavy
            if force_monitor:
                current_monitor = force_monitor
            else:
                result = self._monitor_offset(pixel)
                if result is None:
                    continue
                current_monitor, pixel = result
            width_multiplier = self.image.width() / current_monitor[0]
            height_multiplier = self.image.height() / current_monitor[1]

            # Downscale the pixel to match the pixmap
            x = int(pixel[0] * width_multiplier)
            y = int(pixel[1] * height_multiplier)

            # Send (unique) pixels to be drawn
            if (x, y) not in seen:
                self.update_pixmap_pixel(int(x), int(y), self.pixel_colour)
                seen.add((x, y))

    @QtCore.Slot(int, int, QtGui.QColor)
    def update_pixmap_pixel(self, x: int, y: int, colour: QtGui.QColor) -> None:
        """Update a specific pixel in the QImage and refresh the display."""
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
