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

from mousetracks.misc import get_script_path
from mousetracks.image import colours
from .. import ipc
from ...ui.main import Ui_MainWindow
from ...constants import COMPRESSION_FACTOR, COMPRESSION_THRESHOLD, DEFAULT_PROFILE_NAME, RADIAL_ARRAY_SIZE
from ...constants import UPDATES_PER_SECOND, INACTIVITY_MS
from ...file import get_profile_names
from ...utils.math import calculate_line, calculate_distance, calculate_pixel_offset
from ...utils.win import cursor_position, monitor_locations, SCROLL_EVENTS, MOUSE_OPCODES
from ...ui.widgets import Pixel


ICON_PATH = os.path.join(get_script_path(), 'resources/images/icon.png')


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
    counter: int = field(default=0)


def format_distance(pixels: float, ppi: float = 96.0) -> str:
    """Convert mouse distance to text"""
    inches = pixels / ppi
    cm = inches * 2.54
    m = cm / 100
    km = m / 1000
    if km > 1:
        return f'{round(km, 3)} km'
    if m > 1:
        return f'{round(m, 3)} m'
    return f'{round(cm, 3)} cm'


def format_ticks(ticks: int) -> str:
    """Convert ticks to a formatted time string."""
    seconds = ticks / UPDATES_PER_SECOND
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)

    return f'{int(days):02}:{int(hours):02}:{int(minutes):02}:{seconds:04.1f}'


def format_bytes(b: int) -> str:
    """Convert bytes to a formatted string."""
    if b < 1024:
        return f'{round(b)} B'
    power = min(7, int(math.log(b) / math.log(1024)))
    adjusted = round(b / 1024 ** power, 2)
    sign = 'KMGTPEZY'[power - 1]
    return f'{adjusted} {sign}B'


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
        self.setWindowIcon(QtGui.QIcon(ICON_PATH))
        self.q_send = q_send
        self.q_receive = q_receive

        self.pause_redraw = 0
        self.pause_colour_change = False
        self.redraw_queue: list[tuple[int, int, QtGui.QColor]] = []

        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.ui.output_logs.setVisible(False)

        # Set up profiles
        self.ui.current_profile.clear()
        self.ui.current_profile.addItem('Current Profile')
        for profile in get_profile_names():
            self.ui.current_profile.addItem(profile, profile)

        # self.ui.map_type = QtWidgets.QComboBox()
        self.ui.map_type.addItem('Time', ipc.RenderType.Time)
        self.ui.map_type.addItem('Time (since pause)', ipc.RenderType.TimeSincePause)
        self.ui.map_type.addItem('Time (heatmap)', ipc.RenderType.TimeHeatmap)
        self.ui.map_type.addItem('Speed', ipc.RenderType.Speed)
        self.ui.map_type.addItem('Clicks', ipc.RenderType.SingleClick)
        self.ui.map_type.addItem('Double Clicks', ipc.RenderType.DoubleClick)
        self.ui.map_type.addItem('Held Clicks', ipc.RenderType.HeldClick)
        self.ui.map_type.addItem('Left Thumbstick', ipc.RenderType.Thumbstick_L)
        self.ui.map_type.addItem('Right Thumbstick', ipc.RenderType.Thumbstick_R)
        self.ui.map_type.addItem('Left Thumbstick (heatmap)', ipc.RenderType.Thumbstick_L_Heatmap)
        self.ui.map_type.addItem('Right Thumbstick (heatmap)', ipc.RenderType.Thumbstick_R_Heatmap)
        self.ui.map_type.addItem('Left Thumbstick (speed)', ipc.RenderType.Thumbstick_L_SPEED)
        self.ui.map_type.addItem('Right Thumbstick (speed)', ipc.RenderType.Thumbstick_R_SPEED)

        # Thumbnail pixmap
        self.ui.thumbnail.setPixmap(QtGui.QPixmap(640, 400))

        self.cursor_data = MapData(cursor_position())
        self.thumbstick_l_data = MapData((0, 0))
        self.thumbstick_r_data = MapData((0, 0))

        self.mouse_click_count = self.mouse_held_count = self.mouse_scroll_count = 0
        self.button_press_count = self.key_press_count = 0
        self.elapsed_time = self.active_time = self.inactive_time = 0
        self.monitor_data = monitor_locations()
        self.render_type = ipc.RenderType.Time
        self.render_colour = 'BlackToRedToWhite'
        self.tick_current = 0
        self.last_render: tuple[ipc.RenderType, int] = (self.render_type, -1)
        self.current_app: str = DEFAULT_PROFILE_NAME
        self.current_app_position: Optional[tuple[int, int, int, int]] = None
        self.last_click: Optional[int] = None
        self._bytes_sent = self.bytes_sent = 0
        self._bytes_recv = self.bytes_recv = 0

        # Start queue worker
        self.queue_thread = QtCore.QThread()
        self.queue_worker = QueueWorker(q_receive)
        self.queue_worker.moveToThread(self.queue_thread)

        self.timer_activity = QtCore.QTimer(self)
        self.timer_resize = QtCore.QTimer(self)
        self.timer_resize.setSingleShot(True)

        # Connect signals and slots
        self.ui.file_tracking_start.triggered.connect(self.start_tracking)
        self.ui.file_tracking_pause.triggered.connect(self.pause_tracking)
        self.ui.save_render.clicked.connect(self.render)
        self.ui.current_profile.currentIndexChanged.connect(self.profile_changed)
        self.ui.map_type.currentIndexChanged.connect(self.render_type_changed)
        self.ui.colour_option.currentTextChanged.connect(self.render_colour_changed)
        self.queue_worker.message_received.connect(self.process_message)
        self.queue_thread.started.connect(self.queue_worker.run)
        self.queue_thread.finished.connect(self.queue_worker.deleteLater)
        self.timer_activity.timeout.connect(self.update_activity_preview)
        self.timer_resize.timeout.connect(self.update_thumbnail_size)

        self.ui.debug_tracking_start.triggered.connect(self.start_tracking)
        self.ui.debug_tracking_pause.triggered.connect(self.pause_tracking)
        self.ui.debug_tracking_stop.triggered.connect(self.stop_tracking)
        self.ui.debug_raise_app.triggered.connect(self.raise_app_detection)
        self.ui.debug_raise_tracking.triggered.connect(self.raise_tracking)
        self.ui.debug_raise_processing.triggered.connect(self.raise_processing)
        self.ui.debug_raise_gui.triggered.connect(self.raise_gui)
        self.ui.debug_raise_hub.triggered.connect(self.raise_hub)

        # Start the thread
        self.queue_thread.start()
        self.timer_activity.start(100)

        self.start_tracking()

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
        try:
            self.pixel_colour = colours.calculate_colour_map(colour)[-1]
        except Exception:  # Old code - just fallback to tranparent
            self._render_colour = 'TransparentBlack'
            self.pixel_colour = (0, 0, 0, 0)

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
        previous_text = self.ui.colour_option.currentText()

        self.ui.colour_option.clear()
        self.ui.colour_option.addItem('BlackToRedToWhite')
        for data in colours.parse_colour_file()['Maps'].values():
            match render_type:
                case (ipc.RenderType.Time| ipc.RenderType.TimeSincePause | ipc.RenderType.Speed
                      | ipc.RenderType.Thumbstick_L | ipc.RenderType.Thumbstick_R
                      | ipc.RenderType.Thumbstick_L_SPEED | ipc.RenderType.Thumbstick_R_SPEED):
                    if data['Type']['tracks']:
                        self.ui.colour_option.addItem(data['UpperCase'])
                case (ipc.RenderType.SingleClick | ipc.RenderType.DoubleClick | ipc.RenderType.HeldClick
                      | ipc.RenderType.Thumbstick_L_Heatmap | ipc.RenderType.Thumbstick_R_Heatmap
                      | ipc.RenderType.TimeHeatmap):
                    if data['Type']['clicks']:
                        self.ui.colour_option.addItem(data['UpperCase'])

        # Load previous colour if available, otherwise revert to default
        if previous_text and previous_text != self.ui.colour_option.currentText():
            if idx := self.ui.colour_option.findText(previous_text) < -1:
                self.ui.colour_option.setCurrentIndex(idx)
            self.render_colour = self.ui.colour_option.currentText()

        self.pause_colour_change = False

    @property
    def mouse_click_count(self) -> int:
        """Get the current mouse click count."""
        return self._mouse_click_count

    @mouse_click_count.setter
    def mouse_click_count(self, count: int) -> None:
        """Set the current mouse click count."""
        self._mouse_click_count = count
        self.ui.stat_clicks.setText(str(count))

    @property
    def mouse_scroll_count(self) -> int:
        """Get the current mouse scroll count."""
        return self._mouse_scroll_count

    @mouse_scroll_count.setter
    def mouse_scroll_count(self, count: int) -> None:
        """Set the current mouse scroll count."""
        self._mouse_scroll_count = count
        self.ui.stat_scroll.setText(str(count))

    @property
    def key_press_count(self) -> int:
        """Get the current key press count."""
        return self._key_press_count

    @key_press_count.setter
    def key_press_count(self, count: int) -> None:
        """Set the current key press count."""
        self._key_press_count = count
        self.ui.stat_keys.setText(str(count))

    @property
    def button_press_count(self) -> int:
        """Get the current button press count."""
        return self._button_press_count

    @button_press_count.setter
    def button_press_count(self, count: int) -> None:
        """Set the current button press count."""
        self._button_press_count = count
        self.ui.stat_buttons.setText(str(count))

    @property
    def elapsed_time(self) -> int:
        """Get the current active time."""
        return self._elapsed_time

    @elapsed_time.setter
    def elapsed_time(self, ticks: int) -> None:
        """Set the current active time."""
        self._elapsed_time = ticks

    @property
    def inactive_time(self) -> int:
        """Get the current inactive time."""
        return self._inactive_time

    @inactive_time.setter
    def inactive_time(self, ticks: int) -> None:
        """Set the current inactive time."""
        self._inactive_time = ticks

    def update_activity_preview(self) -> None:
        """Update the activity preview periodically.
        The updates are too frequent to do per tick.
        """
        active_time = self.active_time
        inactive_time = self.inactive_time

        # The active and inactive time don't update every tick
        # Add the difference to keep the GUI in sync
        inactivity_threshold = UPDATES_PER_SECOND * INACTIVITY_MS / 1000
        tick_diff = self.elapsed_time - (self.active_time + self.inactive_time)
        if tick_diff > inactivity_threshold:
            inactive_time += tick_diff
        else:
            active_time += tick_diff

        self.ui.stat_elapsed.setText(format_ticks(self.elapsed_time))
        self.ui.stat_active.setText(format_ticks(active_time))
        self.ui.stat_inactive.setText(format_ticks(inactive_time))

    @property
    def bytes_sent(self) -> int:
        """Get the current bytes sent."""
        return self._bytes_sent

    @bytes_sent.setter
    def bytes_sent(self, amount: int) -> None:
        """Add a delta to the current bytes sent."""
        self._bytes_sent = amount
        self.ui.stat_upload_total.setText(format_bytes(amount))

    @property
    def bytes_recv(self) -> int:
        """Get the current bytes received."""
        return self._bytes_recv

    @bytes_recv.setter
    def bytes_recv(self, amount: int) -> None:
        """Add a delta to the current bytes received."""
        self._bytes_recv = amount
        self.ui.stat_download_total.setText(format_bytes(amount))

    @QtCore.Slot(int)
    def profile_changed(self, idx: int) -> None:
        """Change the profile and trigger a redraw."""
        self.request_thumbnail(force=True)

    @QtCore.Slot(int)
    def render_type_changed(self, idx: int) -> None:
        """Change the render type and trigger a redraw."""
        self.render_type = self.ui.map_type.itemData(idx)
        self.request_thumbnail(force=True)

    @QtCore.Slot(str)
    def render_colour_changed(self, colour: str) -> None:
        """Change the render colour and trigger a redraw."""
        if self.pause_colour_change:
            return
        self.render_colour = colour
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
        self.pause_redraw += 1
        app = self.ui.current_profile.currentData() if self.ui.current_profile.currentIndex() else ''
        size = self.ui.thumbnail.pixmapSize()
        self.q_send.put(ipc.RenderRequest(self.render_type, size.width(), size.height(),
                                          self.render_colour, 1, app, True))
        return True

    def render(self) -> None:
        """Send a render request."""
        app = self.ui.current_profile.currentData() if self.ui.current_profile.currentIndex() else ''
        self.q_send.put(ipc.RenderRequest(self.render_type, None, None,
                                          self.render_colour, self.ui.render_samples.value(), app, False))

    def thumbnail_render_check(self, update_smoothness: int = 4) -> None:
        """Check if the thumbnail should be re-rendered."""
        match self.render_type:
            # This does it every 10, 20, ..., 90, 100, 200, ..., 900, 1000, 2000, etc
            case ipc.RenderType.Time:
                count = self.cursor_data.counter
                update_frequency = min(20000, 10 ** int(math.log10(max(10, count))))
            # With speed it must be constant, doesn't work as well live
            case ipc.RenderType.Speed | ipc.RenderType.TimeSincePause | ipc.RenderType.TimeHeatmap:
                update_frequency = 50
                count = self.cursor_data.counter
            case ipc.RenderType.SingleClick | ipc.RenderType.DoubleClick:
                update_frequency = 1
                count = self.mouse_click_count
            case ipc.RenderType.HeldClick:
                update_frequency = 50
                count = self.mouse_held_count
            case ipc.RenderType.Thumbstick_L:
                count = self.thumbstick_l_data.counter
                update_frequency = min(20000, 10 ** int(math.log10(max(10, count))))
            case ipc.RenderType.Thumbstick_R:
                count = self.thumbstick_r_data.counter
                update_frequency = min(20000, 10 ** int(math.log10(max(10, count))))
            case ipc.RenderType.Thumbstick_L_SPEED | ipc.RenderType.Thumbstick_L_Heatmap:
                count = self.thumbstick_l_data.counter
                update_frequency = 50
            case ipc.RenderType.Thumbstick_R_SPEED | ipc.RenderType.Thumbstick_R_Heatmap:
                count = self.thumbstick_r_data.counter
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
                self.elapsed_time += 1
                self.thumbnail_render_check()

            case ipc.Active():
                self.active_time += message.ticks

            case ipc.Inactive():
                self.inactive_time += message.ticks

            # When monitors change, store the new data
            case ipc.MonitorsChanged():
                self.monitor_data = message.data

            case ipc.Render():
                height, width, channels = message.array.shape

                target_height = int(height / message.sampling)
                target_width = int(width / message.sampling)

                # Draw the new pixmap
                if message.thumbnail:
                    match channels:
                        case 1:
                            image_format = QtGui.QImage.Format.Format_Grayscale8
                        case 3:
                            image_format = QtGui.QImage.Format.Format_RGB888
                        case 4:
                            image_format = QtGui.QImage.Format.Format_RGBA8888
                        case _:
                            raise NotImplementedError(channels)
                    image = QtGui.QImage(message.array.data, width, height, image_format)

                    # Scale the QImage to fit the pixmap size
                    scaled_image = image.scaled(target_width, target_height, QtCore.Qt.AspectRatioMode.KeepAspectRatio)
                    self.ui.thumbnail.setImage(scaled_image)
                    self.pause_redraw -= 1

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
                self.last_click = self.tick_current

            case ipc.MouseHeld():
                self.mouse_held_count += 1
                self.last_click = self.tick_current

            case ipc.MouseMove():
                if self.render_type in (ipc.RenderType.Time, ipc.RenderType.TimeSincePause):
                    self.draw_pixmap_line(message.position, self.cursor_data.position)
                self.update_track_data(self.cursor_data, message.position)
                self.ui.stat_distance.setText(format_distance(self.cursor_data.distance))

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
                    self.draw_pixmap_line(remapped, data.position, (RADIAL_ARRAY_SIZE, RADIAL_ARRAY_SIZE))
                self.update_track_data(data, remapped)

            case ipc.KeyPress():
                if message.opcode in MOUSE_OPCODES:
                    self.mouse_click_count += 1
                else:
                    self.key_press_count += 1

            case ipc.KeyHeld():
                if message.opcode in SCROLL_EVENTS:
                    self.mouse_scroll_count += 1

            case ipc.ButtonPress():
                self.button_press_count += 1

            case ipc.ApplicationDetected():
                for idx in range(1, self.ui.current_profile.count()):
                    if self.ui.current_profile.itemText(idx) == message.name:
                        break
                else:
                    self.ui.current_profile.addItem(message.name, message.name)
                self.current_app = message.name
                self.current_app_position = message.rect
                self.request_thumbnail()

            # Show the correct distance
            case ipc.ProfileLoaded():
                self.cursor_data.distance = message.distance
                self.ui.stat_distance.setText(format_distance(self.cursor_data.distance))
                self.cursor_data.counter = message.cursor_counter
                self.thumbstick_l_data.counter = message.thumb_l_counter
                self.thumbstick_r_data.counter = message.thumb_r_counter

                self.mouse_click_count = message.clicks
                self.mouse_scroll_count = message.scrolls
                self.key_press_count = message.keys_pressed
                self.button_press_count = message.buttons_pressed
                self.elapsed_time = message.elapsed_ticks
                self.active_time = message.active_ticks
                self.inactive_time = message.inactive_ticks
                self.bytes_sent = message.bytes_sent
                self.bytes_recv = message.bytes_recv

            case ipc.DataTransfer():
                self.bytes_sent += message.bytes_sent
                self.bytes_recv += message.bytes_recv

            case ipc.DebugRaiseError():
                raise RuntimeError('[GUI] Test Exception')

    @QtCore.Slot()
    def start_tracking(self) -> None:
        """Start/unpause the script."""
        self.cursor_data.position = cursor_position()  # Prevent erroneous line jumps
        self.q_send.put(ipc.TrackingState(ipc.TrackingState.State.Start))

    @QtCore.Slot()
    def pause_tracking(self) -> None:
        """Pause/unpause the script."""
        self.q_send.put(ipc.TrackingState(ipc.TrackingState.State.Pause))

        # Special case to redraw thumbnail
        if self.ui.map_type.currentData() == ipc.RenderType.TimeSincePause:
            self.request_thumbnail()

    @QtCore.Slot()
    def stop_tracking(self) -> None:
        """Stop the script."""
        self.q_send.put(ipc.TrackingState(ipc.TrackingState.State.Stop))

    @QtCore.Slot()
    def raise_tracking(self) -> None:
        """Send a command to raise an exception.
        For testing purposes only.
        """
        self.q_send.put(ipc.DebugRaiseError(ipc.Target.Tracking))

    @QtCore.Slot()
    def raise_processing(self) -> None:
        """Send a command to raise an exception.
        For testing purposes only.
        """
        self.q_send.put(ipc.DebugRaiseError(ipc.Target.Processing))

    @QtCore.Slot()
    def raise_hub(self) -> None:
        """Send a command to raise an exception.
        For testing purposes only.
        """
        self.q_send.put(ipc.DebugRaiseError(ipc.Target.Hub))

    @QtCore.Slot()
    def raise_app_detection(self) -> None:
        """Send a command to raise an exception.
        For testing purposes only.
        """
        self.q_send.put(ipc.DebugRaiseError(ipc.Target.AppDetection))

    @QtCore.Slot()
    def raise_gui(self) -> None:
        """Send a command to raise an exception.
        For testing purposes only.
        """
        self.q_send.put(ipc.DebugRaiseError(ipc.Target.GUI))

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
        data.distance += calculate_distance(position, data.position)

        # Update the saved data
        data.counter += 1
        data.position = position

        # Check if array compression has been done
        if data.counter > COMPRESSION_THRESHOLD:
            data.counter = int(data.counter / COMPRESSION_FACTOR)

    def draw_pixmap_line(self, old_position: Optional[tuple[int, int]], new_position: Optional[tuple[int, int]],
                         force_monitor: Optional[tuple[int, int]] = None):
        """When an object moves, draw it.
        The drawing is an approximation and not a render, and will be
        periodically replaced with an actual render.
        """
        if self.ui.current_profile.currentIndex() and self.ui.current_profile.currentData() != self.current_app:
            return

        unique_pixels = set()
        size = self.ui.thumbnail.pixmapSize()
        for pixel in calculate_line(old_position, new_position):
            # Refresh data per pixel
            if force_monitor:
                current_monitor = force_monitor
            else:
                result = self._monitor_offset(pixel)
                if result is None:
                    continue
                current_monitor, pixel = result
            width_multiplier = size.width() / current_monitor[0]
            height_multiplier = size.height() / current_monitor[1]

            # Downscale the pixel to match the pixmap
            x = int(pixel[0] * width_multiplier)
            y = int(pixel[1] * height_multiplier)
            unique_pixels.add((x, y))

        # Send unique pixels to be drawn
        self.update_pixmap_pixels(*(Pixel(QtCore.QPoint(x, y), self.pixel_colour) for x, y in unique_pixels))

    @QtCore.Slot(int, int, QtGui.QColor)
    def update_pixmap_pixels(self, *pixels: Pixel) -> None:
        """Update a specific pixel in the QImage and refresh the display."""
        self.ui.thumbnail.updatePixels(*pixels)

        # Queue commands if redrawing is paused
        # This allows them to be resubmitted after an update
        if self.pause_redraw:
            self.redraw_queue.extend(pixels)
        elif self.redraw_queue:
            redraw_queue, self.redraw_queue = self.redraw_queue, []
            self.ui.thumbnail.updatePixels(*redraw_queue)

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        """Start a timer to trigger after resizing has finished."""
        self.timer_resize.start(100)
        super().resizeEvent(event)

    def update_thumbnail_size(self) -> None:
        """Set a new thumbnail size after the window has finished resizing."""
        self.ui.thumbnail.freezeScale()
        self.request_thumbnail()


def run(q_send: multiprocessing.Queue, q_receive: multiprocessing.Queue) -> None:
    app = QtWidgets.QApplication(sys.argv)

    # Register app so that setting an icon is possible
    if os.name == "nt":
        import ctypes
        myappid = "uk.huntfx.mousetracks"
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

    m = MainWindow(q_send, q_receive)
    m.show()
    icon = QtGui.QIcon(ICON_PATH)
    app.setWindowIcon(icon)
    app.exec()