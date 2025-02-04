from __future__ import annotations

import os
import math
import sys
import time
from contextlib import suppress
from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING

from PIL import Image
from PySide6 import QtCore, QtWidgets, QtGui

from mousetracks.image import colours
from .ui import layout
from .utils import format_distance, format_ticks, format_bytes, ICON_PATH
from .widgets import Pixel
from .. import ipc
from ...config import GlobalConfig
from ...constants import COMPRESSION_FACTOR, COMPRESSION_THRESHOLD, DEFAULT_PROFILE_NAME, RADIAL_ARRAY_SIZE
from ...constants import UPDATES_PER_SECOND, INACTIVITY_MS, IS_EXE, SHUTDOWN_TIMEOUT
from ...file import get_profile_names
from ...utils import keycodes
from ...utils.math import calculate_line, calculate_distance, calculate_pixel_offset
from ...utils.win import cursor_position, monitor_locations, AutoRun

if TYPE_CHECKING:
    from . import GUI


@dataclass
class MapData:
    position: tuple[int, int] | None = field(default_factory=cursor_position)
    distance: float = field(default=0.0)
    counter: int = field(default=0)


@dataclass
class Profile:
    """Hold data related to the currently running profile."""

    name: str
    rect: tuple[int, int, int, int] | None = None
    track_mouse: bool = True
    track_keyboard: bool = True
    track_gamepad: bool = True
    track_network: bool = True


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

    exception_raised = QtCore.Signal(Exception)

    close_splash_screen = QtCore.Signal()

    def __init__(self, component: GUI) -> None:
        super().__init__()
        self.setWindowIcon(QtGui.QIcon(ICON_PATH))
        self.component = component
        self.config = GlobalConfig()

        self.pause_redraw = 0
        self.pause_colour_change = False
        self.redraw_queue: list[Pixel] = []
        self._last_save_time = self._last_thumbnail_time = time.time()
        self._delete_mouse_pressed = False
        self._delete_keyboard_pressed = False
        self._delete_gamepad_pressed = False
        self._delete_network_pressed = False
        self._profile_names = get_profile_names()
        self._unsaved_profiles: set[str] = set()
        self._redrawing_profiles = False
        self._is_loading_profile = 0
        self._is_closing = False

        self.ui = layout.Ui_MainWindow()
        self.ui.setupUi(self)

        # Set initial widget states
        self.ui.output_logs.setVisible(False)
        self.ui.tray_context_menu.menuAction().setVisible(False)
        try:
            self.ui.prefs_autorun.setChecked(bool(AutoRun()))
        except ValueError:
            self.ui.prefs_autorun.setEnabled(False)
        self.ui.prefs_automin.setChecked(self.config.minimise_on_start)
        self.ui.prefs_console.setChecked(not IS_EXE)

        # Store things for full screen
        # The `addAction` is required for a hidden menubar
        self.addAction(self.ui.full_screen)
        self._margins_main = self.ui.main_layout.contentsMargins()
        self._margins_render = self.ui.main_layout.contentsMargins()

        # Set up the tray icon
        self.tray: QtWidgets.QSystemTrayIcon | None
        if QtWidgets.QSystemTrayIcon.isSystemTrayAvailable():
            self.tray = QtWidgets.QSystemTrayIcon(self)
            self.tray.setIcon(QtGui.QIcon(ICON_PATH))
            self.tray.setContextMenu(self.ui.tray_context_menu)
            self.tray.activated.connect(self.tray_activated)
            self.tray.show()
        else:
            self.tray = None
            self.ui.menu_allow_minimise.setChecked(False)
            self.ui.menu_allow_minimise.setEnabled(False)

        self.current_profile = Profile(DEFAULT_PROFILE_NAME)
        #self.update_profile_combobox(DEFAULT_PROFILE_NAME)

        # self.ui.map_type = QtWidgets.QComboBox()
        self.ui.map_type.addItem('[Mouse] Time', ipc.RenderType.Time)
        self.ui.map_type.addItem('[Mouse] Heatmap', ipc.RenderType.TimeHeatmap)
        self.ui.map_type.addItem('[Mouse] Speed', ipc.RenderType.Speed)
        self.ui.map_type.addItem('[Mouse] Clicks', ipc.RenderType.SingleClick)
        self.ui.map_type.addItem('[Mouse] Double Clicks', ipc.RenderType.DoubleClick)
        self.ui.map_type.addItem('[Mouse] Held Clicks', ipc.RenderType.HeldClick)
        self.ui.map_type.addItem('[Keyboard] Key Presses', ipc.RenderType.Keyboard)
        self.ui.map_type.addItem('[Gamepad] Thumbstick Time', ipc.RenderType.Thumbstick_Time)
        self.ui.map_type.addItem('[Gamepad] Thumbstick Heatmap', ipc.RenderType.Thumbstick_Heatmap)
        self.ui.map_type.addItem('[Gamepad] Thumbstick Speed', ipc.RenderType.Thumbstick_Speed)

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
        self.save_request_sent = False
        self._bytes_sent = self.bytes_sent = 0
        self._bytes_recv = self.bytes_recv = 0

        self.timer_activity = QtCore.QTimer(self)
        self.timer_resize = QtCore.QTimer(self)
        self.timer_resize.setSingleShot(True)
        self.timer_rendering = QtCore.QTimer(self)
        self.timer_rendering.setSingleShot(True)

        # Connect signals and slots
        self.ui.menu_exit.triggered.connect(self.shut_down)
        self.ui.file_tracking_start.triggered.connect(self.start_tracking)
        self.ui.file_tracking_pause.triggered.connect(self.pause_tracking)
        self.ui.save_render.clicked.connect(self.request_render)
        self.ui.current_profile.currentIndexChanged.connect(self.profile_changed)
        self.ui.map_type.currentIndexChanged.connect(self.render_type_changed)
        self.ui.colour_option.currentTextChanged.connect(self.render_colour_changed)
        self.ui.auto_switch_profile.stateChanged.connect(self.toggle_auto_switch_profile)
        self.ui.thumbnail_refresh.clicked.connect(self.request_thumbnail)
        self.ui.thumbnail.resized.connect(self.thumbnail_resize)
        self.ui.thumbnail.clicked.connect(self.thumbnail_click)
        self.ui.track_mouse.stateChanged.connect(self.handle_delete_button_visibility)
        self.ui.track_keyboard.stateChanged.connect(self.handle_delete_button_visibility)
        self.ui.track_gamepad.stateChanged.connect(self.handle_delete_button_visibility)
        self.ui.track_network.stateChanged.connect(self.handle_delete_button_visibility)
        self.ui.track_mouse.stateChanged.connect(self.toggle_profile_mouse_tracking)
        self.ui.track_keyboard.stateChanged.connect(self.toggle_profile_keyboard_tracking)
        self.ui.track_gamepad.stateChanged.connect(self.toggle_profile_gamepad_tracking)
        self.ui.track_network.stateChanged.connect(self.toggle_profile_network_tracking)
        self.ui.delete_mouse.clicked.connect(self.delete_mouse)
        self.ui.delete_keyboard.clicked.connect(self.delete_keyboard)
        self.ui.delete_gamepad.clicked.connect(self.delete_gamepad)
        self.ui.delete_network.clicked.connect(self.delete_network)
        self.ui.autosave.stateChanged.connect(self.toggle_autosave)
        self.ui.file_save.triggered.connect(self.manual_save)
        self.ui.tray_show.triggered.connect(self.load_from_tray)
        self.ui.tray_hide.triggered.connect(self.hide_to_tray)
        self.ui.tray_exit.triggered.connect(self.shut_down)
        self.ui.prefs_autorun.triggered.connect(self.set_autorun)
        self.ui.prefs_automin.triggered.connect(self.set_minimise_on_start)
        self.ui.prefs_console.triggered.connect(self.toggle_console)
        self.ui.full_screen.triggered.connect(self.toggle_full_screen)
        self.timer_activity.timeout.connect(self.update_activity_preview)
        self.timer_activity.timeout.connect(self.update_time_since_save)
        self.timer_activity.timeout.connect(self.update_time_since_thumbnail)
        self.timer_activity.timeout.connect(self.update_queue_size)
        self.timer_resize.timeout.connect(self.update_thumbnail_size)
        self.timer_rendering.timeout.connect(self.ui.thumbnail.show_rendering_text)

        self.ui.debug_tracking_start.triggered.connect(self.start_tracking)
        self.ui.debug_tracking_pause.triggered.connect(self.pause_tracking)
        self.ui.debug_tracking_stop.triggered.connect(self.stop_tracking)
        self.ui.debug_raise_app.triggered.connect(self.raise_app_detection)
        self.ui.debug_raise_tracking.triggered.connect(self.raise_tracking)
        self.ui.debug_raise_processing.triggered.connect(self.raise_processing)
        self.ui.debug_raise_gui.triggered.connect(self.raise_gui)
        self.ui.debug_raise_hub.triggered.connect(self.raise_hub)

        # Trigger initial setup
        self.profile_changed(0)

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
            self.pixel_colour = QtGui.QColor(*colours.calculate_colour_map(colour)[-1])
        except Exception:  # Old code - just fallback to tranparent
            self._render_colour = 'TransparentBlack'
            self.pixel_colour = QtGui.QColor(QtCore.Qt.GlobalColor.black)

    @property
    def pixel_colour(self) -> QtGui.QColor:
        """Get the pixel colour to draw with."""
        return self._pixel_colour

    @pixel_colour.setter
    def pixel_colour(self, colour: QtGui.QColor):
        """Set the pixel colour to draw with."""
        self._pixel_colour = colour

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

        colour_maps = colours.get_map_matches(
            tracks=render_type in (ipc.RenderType.Time, ipc.RenderType.Speed,
                                   ipc.RenderType.Thumbstick_Time, ipc.RenderType.Thumbstick_Speed),
            clicks=render_type in (ipc.RenderType.SingleClick, ipc.RenderType.DoubleClick, ipc.RenderType.HeldClick,
                                   ipc.RenderType.Thumbstick_Heatmap, ipc.RenderType.TimeHeatmap),
            keyboard=render_type == ipc.RenderType.Keyboard,
        )
        self.ui.colour_option.addItems(colour_maps)

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

    @property
    def save_request_sent(self) -> bool:
        """If waiting on a save request."""
        return self._save_request_sent

    @save_request_sent.setter
    def save_request_sent(self, value: bool) -> None:
        """Set when waiting on a save request.
        This blocks the save action from triggering.
        """
        self._save_request_sent = value
        self.ui.save.setEnabled(not value)
        self.ui.file_save.setEnabled(not value)

    @QtCore.Slot()
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

    @QtCore.Slot()
    def update_time_since_save(self) -> None:
        """Set how long it has been since the last save."""
        self.ui.time_since_save.setText(f'{round(time.time() - self._last_save_time, 1)} s')

    @QtCore.Slot()
    def update_time_since_thumbnail(self) -> None:
        """Set how long it has been since the last thumbnail render."""
        self.ui.time_since_thumbnail.setText(f'{round(time.time() - self._last_thumbnail_time, 1)} s')

    def update_queue_size(self) -> None:
        """Request an update of the queue size."""
        self.component.send_data(ipc.RequestQueueSize())

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

    @property
    def current_profile(self) -> Profile:
        """Get the currently running profile."""
        return self._current_profile

    @current_profile.setter
    def current_profile(self, profile: Profile) -> None:
        """Set the currently running profile.

        This will automatically update the combobox, but will not
        trigger a thumbnail update.
        """
        self._current_profile = profile

        # Update the profile order
        with suppress(ValueError):
            del self._profile_names[self._profile_names.index(profile.name)]
        self._profile_names.insert(0, profile.name)
        self._unsaved_profiles.add(profile.name)
        self._redraw_profile_combobox()

    def _redraw_profile_combobox(self) -> None:
        """Redraw the profile combobox.
        Any "modified" profiles will have an asterix in front.
        """
        # Pause the signals
        self._redrawing_profiles = True

        # Grab the currently selected profile
        current = self.ui.current_profile.currentData()

        # Add the profiles
        self.ui.current_profile.clear()
        for profile in self._profile_names:
            if profile in self._unsaved_profiles:
                self.ui.current_profile.addItem(f'*{profile}', profile)
            else:
                self.ui.current_profile.addItem(profile, profile)

        # Change back to the previously selected profile
        if self.ui.auto_switch_profile.isChecked():
            self.ui.current_profile.setCurrentIndex(0)
        else:
            idx = self.ui.current_profile.findData(current)
            if idx != -1:
                self.ui.current_profile.setCurrentIndex(idx)

        # Resume signals
        self._redrawing_profiles = False

    @QtCore.Slot()
    def manual_save(self) -> None:
        """Trigger a manual save request."""
        if self.save_request_sent:
            return
        self.save_request_sent = True
        self.component.send_data(ipc.Save())

    @QtCore.Slot(QtCore.Qt.CheckState)
    def toggle_autosave(self, state: QtCore.Qt.CheckState) -> None:
        """Enable or disable autosaving."""
        self.component.send_data(ipc.Autosave(state == QtCore.Qt.CheckState.Checked.value))

    @QtCore.Slot(int)
    def profile_changed(self, idx: int) -> None:
        """Change the profile and trigger a redraw."""
        self.ui.tab_options.setTabText(1, f'{self.ui.current_profile.itemData(idx)} Options')

        if not self._redrawing_profiles:
            self.request_profile_data(self.ui.current_profile.itemData(idx))
            if idx:
                self.ui.auto_switch_profile.setChecked(False)

    def request_profile_data(self, profile_name: str) -> None:
        """Request loading profile data."""
        self.component.send_data(ipc.ProfileDataRequest(profile_name))
        self._is_loading_profile += 1
        self.start_rendering_timer()

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

    @QtCore.Slot(QtCore.Qt.CheckState)
    def toggle_auto_switch_profile(self, state: QtCore.Qt.CheckState) -> None:
        """Switch to the current profile when auto switch is checked."""
        if state == QtCore.Qt.CheckState.Checked.value:
            self.ui.current_profile.setCurrentIndex(0)

    def _monitor_offset(self, pixel: tuple[int, int]) -> tuple[tuple[int, int], tuple[int, int]] | None:
        """Detect which monitor the pixel is on."""
        if self.current_profile.rect is not None:
            monitor_data = [self.current_profile.rect]
        else:
            monitor_data = self.monitor_data

        for x1, y1, x2, y2 in monitor_data:
            result = calculate_pixel_offset(pixel[0], pixel[1], x1, y1, x2, y2)
            if result is not None:
                return result
        return None

    def start_rendering_timer(self):
        """Start the timer to display rendering text.

        If a render is not completed within 1 second, then text will be
        drawn to the preview to update the user.
        """
        if not self.timer_rendering.isActive():
            self.timer_rendering.start(1000)


    def request_thumbnail(self, force: bool = False) -> bool:
        """Send a request to draw a thumbnail.
        This will start pooling mouse move data to be redrawn after.
        """
        # Block when minimised
        if not self.isVisible():
            return False

        # If already redrawing then prevent building up duplicate commands
        if self.pause_redraw and not force:
            return False
        self.pause_redraw += 1

        width = self.ui.thumbnail.width()
        height = self.ui.thumbnail.height()
        profile = self.ui.current_profile.currentData()

        # Account for collapsed splitters
        if not self.ui.horizontal_splitter.sizes()[1] and self.ui.horizontal_splitter.is_handle_visible():
            width += self.ui.horizontal_splitter.handleWidth()
        if not self.ui.vertical_splitter.sizes()[1] and self.ui.vertical_splitter.is_handle_visible():
            height += self.ui.vertical_splitter.handleWidth()

        self.start_rendering_timer()
        self.component.send_data(ipc.RenderRequest(self.render_type, width, height,
                                                   self.render_colour, 1, profile, None))
        return True

    @QtCore.Slot(QtCore.QSize)
    def thumbnail_resize(self, size) -> None:
        """Start the resize timer when the thumbnail changes size.
        This prevents constant render requests as it will only trigger
        after resizing has finished.
        """
        self.timer_resize.start(10)

    @QtCore.Slot(bool)
    def thumbnail_click(self, state: bool) -> None:
        """Handle what to do when the thumbnail is clicked."""
        if state:
            self.start_tracking()
        else:
            self.pause_tracking()

    def request_render(self) -> None:
        """Send a render request."""
        profile = self.ui.current_profile.currentData()

        dialog = QtWidgets.QFileDialog()
        dialog.setAcceptMode(QtWidgets.QFileDialog.AcceptMode.AcceptSave)
        dialog.setNameFilters(['PNG Files (*.png)"'])
        dialog.setDefaultSuffix('png')

        match self.render_type:
            case ipc.RenderType.Time:
                name = 'Mouse Tracks'
            case ipc.RenderType.TimeHeatmap:
                name = 'Mouse Heatmap'
            case ipc.RenderType.Speed:
                name = 'Mouse Speed'
            case ipc.RenderType.SingleClick:
                name = 'Mouse Clicks'
            case ipc.RenderType.DoubleClick:
                name = 'Mouse Double Clicks'
            case ipc.RenderType.HeldClick:
                name = 'Mouse Held Clicks'
            case ipc.RenderType.Thumbstick_Time:
                name = 'Gamepad Thumbstick Tracks'
            case ipc.RenderType.Thumbstick_Heatmap:
                name = 'Gamepad Thumbstick Heatmap'
            case ipc.RenderType.Thumbstick_Speed:
                name = 'Gamepad Thumbstick Speed'
            case _:
                name = 'Tracks'
        filename = f'[{format_ticks(self.elapsed_time)}][{self.render_colour}] {profile} - {name}.png'
        file_path, accept = dialog.getSaveFileName(None, 'Save Image', filename, 'Image Files (*.png)')

        if accept:
            self.component.send_data(ipc.RenderRequest(self.render_type, None, None,
                                                       self.render_colour, self.ui.render_samples.value(),
                                                       profile, file_path))

    def thumbnail_render_check(self, update_smoothness: int = 4) -> None:
        """Check if the thumbnail should be re-rendered."""
        match self.render_type:
            # This does it every 10, 20, ..., 90, 100, 200, ..., 900, 1000, 2000, etc
            case ipc.RenderType.Time:
                count = self.cursor_data.counter
                update_frequency = min(20000, 10 ** int(math.log10(max(10, count))))
            # With speed it must be constant, doesn't work as well live
            case ipc.RenderType.Speed | ipc.RenderType.TimeHeatmap:
                update_frequency = 50
                count = self.cursor_data.counter
            case ipc.RenderType.SingleClick | ipc.RenderType.DoubleClick:
                update_frequency = 1
                count = self.mouse_click_count
            case ipc.RenderType.HeldClick:
                update_frequency = 50
                count = self.mouse_held_count
            case ipc.RenderType.Thumbstick_Time:
                count = self.thumbstick_l_data.counter + self.thumbstick_r_data.counter
                update_frequency = min(20000, 10 ** int(math.log10(max(10, count))))
            case ipc.RenderType.Thumbstick_Speed | ipc.RenderType.Thumbstick_Heatmap:
                count = self.thumbstick_l_data.counter + self.thumbstick_r_data.counter
                update_frequency = 50
            case ipc.RenderType.Keyboard:
                update_frequency = 1
                count = self.key_press_count
            case _:
                return

        # Don't render if there's no data
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

    def process_message(self, message: ipc.Message) -> None:
        """Process messages and send back data if any exception occurs."""
        try:
            self._process_message(message)
        except Exception as e:
            self.exception_raised.emit(e)

    def _process_message(self, message: ipc.Message) -> None:
        """Process messages."""
        match message:
            case ipc.Tick() if self.is_live:
                self.tick_current = message.tick
                self.elapsed_time += 1
                self.thumbnail_render_check()

            case ipc.Active() if self.is_live:
                self.active_time += message.ticks

            case ipc.Inactive() if self.is_live:
                self.inactive_time += message.ticks

            # When monitors change, store the new data
            case ipc.MonitorsChanged():
                self.monitor_data = message.data

            case ipc.Render():
                height, width, channels = message.array.shape
                failed = width == height == 0

                target_height = int(height / message.request.sampling)
                target_width = int(width / message.request.sampling)

                # Draw the new pixmap
                if message.request.file_path is None:
                    self.timer_rendering.stop()
                    self.ui.thumbnail.hide_rendering_text()

                    self._last_thumbnail_time = time.time()
                    match channels:
                        case 1:
                            image_format = QtGui.QImage.Format.Format_Grayscale8
                        case 3:
                            image_format = QtGui.QImage.Format.Format_RGB888
                        case 4:
                            image_format = QtGui.QImage.Format.Format_RGBA8888
                        case _:
                            raise NotImplementedError(channels)

                    if failed:
                        self.ui.thumbnail.set_pixmap(QtGui.QPixmap())

                    else:
                        stride = channels * width
                        image = QtGui.QImage(message.array.data, width, height, stride, image_format)

                        # Scale the QImage to fit the pixmap size
                        scaled_image = image.scaled(target_width, target_height, QtCore.Qt.AspectRatioMode.KeepAspectRatio)
                        self.ui.thumbnail.set_pixmap(scaled_image)

                    self.pause_redraw -= 1

                # Save a render
                elif failed:
                    msg = QtWidgets.QMessageBox(self)
                    msg.setWindowTitle('Render Failed')
                    msg.setIcon(QtWidgets.QMessageBox.Icon.Critical)
                    msg.setText('No data is available for this render.')
                    msg.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Ok)
                    msg.exec_()

                else:
                    im = Image.fromarray(message.array)
                    im = im.resize((target_width, target_height), Image.Resampling.LANCZOS)
                    im.save(message.request.file_path)
                    os.startfile(message.request.file_path)

            case ipc.MouseHeld() if self.is_live and self.ui.track_mouse.isChecked():
                self.mouse_held_count += 1

            case ipc.MouseMove() if self.is_live and self.ui.track_mouse.isChecked():
                if self.render_type == ipc.RenderType.Time:
                    self.draw_pixmap_line(message.position, self.cursor_data.position)
                self.update_track_data(self.cursor_data, message.position)
                self.ui.stat_distance.setText(format_distance(self.cursor_data.distance))

            case ipc.ThumbstickMove() if self.is_live and self.ui.track_gamepad.isChecked():
                match message.thumbstick:
                    case ipc.ThumbstickMove.Thumbstick.Left:
                        data = self.thumbstick_l_data
                        offset = -0.5
                    case ipc.ThumbstickMove.Thumbstick.Right:
                        data = self.thumbstick_r_data
                        offset = 0.5
                    case _:
                        raise NotImplementedError(message.thumbstick)

                x, y = message.position
                x = x * 0.5 + offset  # Required for the side by side display

                remapped = (int(x * 1024 + 1024), int(-y * 1024 + 1024))
                if self.render_type == ipc.RenderType.Thumbstick_Time:
                    self.draw_pixmap_line(remapped, data.position, (RADIAL_ARRAY_SIZE, RADIAL_ARRAY_SIZE))
                self.update_track_data(data, remapped)

            case ipc.KeyPress() if self.is_live and self.ui.track_keyboard.isChecked():
                if message.keycode in keycodes.MOUSE_CODES:
                    self.mouse_click_count += 1

                # If L/R CONTROL, then it also triggers CONTROL
                elif message.keycode in (keycodes.VK_LCONTROL, keycodes.VK_RCONTROL):
                    pass

                # If L MENU, then it also triggers MENU
                elif message.keycode == keycodes.VK_LMENU:
                    pass

                # If R MENU, then it triggers MENU, L CONTROL and CONTROL
                elif message.keycode == keycodes.VK_RMENU:
                    self.key_press_count -= 1

                else:
                    self.key_press_count += 1

            case ipc.KeyHeld() if self.is_live and self.ui.track_keyboard.isChecked():
                if message.keycode in keycodes.SCROLL_CODES:
                    self.mouse_scroll_count += 1

            case ipc.ButtonPress() if self.is_live and self.ui.track_gamepad.isChecked():
                self.button_press_count += 1

            case ipc.ApplicationDetected():
                self.current_profile = Profile(message.name, message.rect)

                if self.is_live:
                    self.request_profile_data(message.name)

            # Show the correct distance
            case ipc.ProfileData():
                self._is_loading_profile -= 1
                finished_loading = not self._is_loading_profile

                # Pause the signals on the track options
                self.ui.track_mouse.setEnabled(False)
                self.ui.track_keyboard.setEnabled(False)
                self.ui.track_gamepad.setEnabled(False)
                self.ui.track_network.setEnabled(False)

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

                if finished_loading:
                    self.request_thumbnail(force=True)

                self.ui.track_mouse.setChecked(message.config.track_mouse)
                self.ui.track_keyboard.setChecked(message.config.track_keyboard)
                self.ui.track_gamepad.setChecked(message.config.track_gamepad)
                self.ui.track_network.setChecked(message.config.track_network)

                # Update the visibility of the delete options
                self._delete_mouse_pressed = False
                self._delete_keyboard_pressed = False
                self._delete_gamepad_pressed = False
                self._delete_network_pressed = False
                self.handle_delete_button_visibility()

                # Resume signals on the track options
                self.ui.track_mouse.setEnabled(finished_loading)
                self.ui.track_keyboard.setEnabled(finished_loading)
                self.ui.track_gamepad.setEnabled(finished_loading)
                self.ui.track_network.setEnabled(finished_loading)

            case ipc.DataTransfer() if self.is_live and self.ui.track_network.isChecked():
                self.bytes_sent += message.bytes_sent
                self.bytes_recv += message.bytes_recv

            case ipc.SaveComplete():
                self._last_save_time = time.time()
                self._unsaved_profiles -= set(message.succeeded)
                self._unsaved_profiles.add(self.current_profile.name)
                self._redraw_profile_combobox()

                # Notify when complete
                if self.save_request_sent:
                    self.save_request_sent = False

                    msg = QtWidgets.QMessageBox(self)
                    msg.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Ok)

                    if message.failed:
                        msg.setWindowTitle('Save Failed')
                        msg.setIcon(QtWidgets.QMessageBox.Icon.Warning)
                        msg.setText('Not all profiles were saved.\n'
                                    f'  Successful: {", ".join(message.succeeded)}\n'
                                    f'  Failed: {", ".join(message.failed)}\n')
                    else:
                        msg.setWindowTitle('Successful')
                        msg.setIcon(QtWidgets.QMessageBox.Icon.Information)
                        msg.setText('All profiles have been saved.')

                    msg.exec_()

            case ipc.DebugRaiseError():
                raise RuntimeError('[GUI] Test Exception')

            case ipc.QueueSize():
                self.ui.stat_hub_queue.setText(str(message.hub))
                self.ui.stat_tracking_queue.setText(str(message.tracking))
                self.ui.stat_processing_queue.setText(str(message.processing))
                self.ui.stat_gui_queue.setText(str(message.gui))
                self.ui.stat_app_detection_queue.setText(str(message.app_detection))

            case ipc.InvalidConsole():
                self.ui.prefs_console.setEnabled(False)

            case ipc.CloseSplashScreen():
                self.close_splash_screen.emit()

    @QtCore.Slot()
    def start_tracking(self) -> None:
        """Start/unpause the script."""
        self.cursor_data.position = cursor_position()  # Prevent erroneous line jumps
        self.component.send_data(ipc.TrackingState(ipc.TrackingState.State.Start))

    @QtCore.Slot()
    def pause_tracking(self) -> None:
        """Pause/unpause the script."""
        self.component.send_data(ipc.TrackingState(ipc.TrackingState.State.Pause))

    @QtCore.Slot()
    def stop_tracking(self) -> None:
        """Stop the script."""
        self.component.send_data(ipc.TrackingState(ipc.TrackingState.State.Stop))

    @QtCore.Slot()
    def raise_tracking(self) -> None:
        """Send a command to raise an exception.
        For testing purposes only.
        """
        self.component.send_data(ipc.DebugRaiseError(ipc.Target.Tracking))

    @QtCore.Slot()
    def raise_processing(self) -> None:
        """Send a command to raise an exception.
        For testing purposes only.
        """
        self.component.send_data(ipc.DebugRaiseError(ipc.Target.Processing))

    @QtCore.Slot()
    def raise_hub(self) -> None:
        """Send a command to raise an exception.
        For testing purposes only.
        """
        self.component.send_data(ipc.DebugRaiseError(ipc.Target.Hub))

    @QtCore.Slot()
    def raise_app_detection(self) -> None:
        """Send a command to raise an exception.
        For testing purposes only.
        """
        self.component.send_data(ipc.DebugRaiseError(ipc.Target.AppDetection))

    @QtCore.Slot()
    def raise_gui(self) -> None:
        """Send a command to raise an exception.
        For testing purposes only.
        """
        self.component.send_data(ipc.DebugRaiseError(ipc.Target.GUI))

    @QtCore.Slot()
    def shut_down(self) -> None:
        """Trigger a safe shutdown of the application."""
        # If invisible then the close event does not end the QApplication
        if not self.isVisible():
            self.show()

        self.close()

    @QtCore.Slot(QtWidgets.QSystemTrayIcon.ActivationReason)
    def tray_activated(self, reason: QtWidgets.QSystemTrayIcon.ActivationReason) -> None:
        """What to do when the tray icon is double clicked."""
        if reason == QtWidgets.QSystemTrayIcon.ActivationReason.DoubleClick:
            self.load_from_tray()

    def hide_to_tray(self) -> None:
        """Minimise the window to the tray."""
        if self.tray is None or not self.ui.menu_allow_minimise.isChecked():
            self.showMinimized()

        elif self.isVisible():
            self.hide()
            self.ui.thumbnail.clear_pixmap()
            self.notify(f'{self.windowTitle()} is now running in the background.')

    def load_from_tray(self):
        """Load the window from the tray icon.
        If the window is only minimised to the taskbar, then `show()`
        will be ignored.
        """
        if self.isMinimized():
            self.setWindowState(QtCore.Qt.WindowState.WindowActive)

        if not self.isVisible():
            self.show()

            if self.ui.full_screen.isChecked():
                self.showFullScreen()

    def showEvent(self, event: QtGui.QShowEvent) -> None:
        """What to do when showing the window.
        The thumbnail is updated and the update timer is resumed.

        Window events are "spontaneous", and internal events are not.

        When the window is first shown, it is not spontaneous.

        When the window is loaded by double clicking the tray icon, or
        by selecting exit (which also calls `.show()`), then it fires
        off a non spontaneous event followed by a spontaneous event.

        When the window is loaded by choosing the option in the tray
        icon, then it is not spontaneous.

        If the window is only minimised to the tray, then it will fire
        off a spontaneous event when shown.

        Based on that information, all the necessary logic should be
        limited to the non spontaneous events.
        """
        if not event.spontaneous():
            self.timer_activity.start(100)
            self.request_thumbnail(force=True)
            self.setWindowState(QtCore.Qt.WindowState.WindowActive)

        event.accept()

    def hideEvent(self, event: QtGui.QHideEvent) -> None:
        """Intercept hide events.
        The update timer stops updating widgets, and the render preview
        is cleared from memory.

        User events are "spontaneous", and application events are not.

        If the user clicks the minimise button, or the taskbar icon,
        then a spontaneous event will be sent to minimise the window.
        The `changeEvent` override will catch this and fire off another
        event to hide the window, which is not spontaneous.

        If the user chooses the tray icon option to minimise, then
        because it originates from the application, it is not
        spontaneous.

        Based on that information, any spontaneous events are simply the
        user manually minimising the application, so a hide needs to be
        triggered. Likewise, any non spontaneous events are for hiding
        the window, so all the code related to that can be put here.
        """
        if event.spontaneous():
            # The application has only been minimised, so fully hide it
            if self.isMinimized() and self.ui.menu_allow_minimise.isChecked():
                self.hide()

        elif not self._is_closing:
            self.timer_activity.stop()
            self.ui.thumbnail.clear_pixmap()
            self.notify(f'{self.windowTitle()} is now running in the background.')

        event.accept()

    def ask_to_save(self, timeout: float = SHUTDOWN_TIMEOUT, accuracy: int = 1) -> bool:
        """Ask the user to save.
        Returns False if the save was cancelled.
        """
        target_timeout = time.time() + timeout

        def update_message() -> None:
            """Updates the countdown message and auto-saves if time runs out."""
            remaining_timeout = round(target_timeout - time.time(), accuracy)
            if remaining_timeout > 0:
                msg.setText('Do you want to save?')
                msg.setInformativeText(f'Saving automatically in {remaining_timeout} seconds...')
            else:
                timer.stop()
                msg.accept()

        # Pause the tracking
        self.component.send_data(ipc.TrackingState(ipc.TrackingState.State.Pause))

        msg = QtWidgets.QMessageBox(self)
        msg.setWindowTitle(f'Closing {self.windowTitle()}')
        msg.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No
                               | QtWidgets.QMessageBox.StandardButton.Cancel)
        update_message()

        # Use a QTimer to update the countdown
        timer = QtCore.QTimer(self)
        timer.timeout.connect(update_message)
        timer.start(10 ** (3 - accuracy))

        match msg.exec_():
            case QtWidgets.QMessageBox.StandardButton.Cancel:
                self.component.send_data(ipc.TrackingState(ipc.TrackingState.State.Start))
                return False

            case QtWidgets.QMessageBox.StandardButton.Yes:
                self.component.send_data(ipc.Save())
        return True

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        """Handle what to do when the GUI is closed."""
        self._is_closing = True
        if self.ask_to_save():
            event.accept()
        else:
            event.ignore()
            self._is_closing = False

    def update_track_data(self, data: MapData, position: tuple[int, int]) -> None:
        data.distance += calculate_distance(position, data.position)

        # Update the saved data
        data.counter += 1
        data.position = position

        # Check if array compression has been done
        if data.counter > COMPRESSION_THRESHOLD:
            data.counter = int(data.counter / COMPRESSION_FACTOR)

    @property
    def is_live(self) -> bool:
        """Determine if the visible data is live."""
        return self.ui.current_profile.currentData() == self.current_profile.name

    def draw_pixmap_line(self, old_position: tuple[int, int] | None, new_position: tuple[int, int] | None,
                         force_monitor: tuple[int, int] | None = None):
        """When an object moves, draw it.
        The drawing is an approximation and not a render, and will be
        periodically replaced with an actual render.
        """
        if not self.isVisible() or not self.is_live or self._is_closing or self.ui.thumbnail.pixmap().isNull():
            return

        unique_pixels = set()
        size = self.ui.thumbnail.pixmap_size()
        for pixel in calculate_line(old_position, new_position):
            # Refresh data per pixel
            if force_monitor:
                current_monitor = force_monitor
            else:
                result = self._monitor_offset(pixel)
                if result is None:
                    continue
                current_monitor, pixel = result
            width_multiplier = (size.width() - 1) / current_monitor[0]
            height_multiplier = (size.height() - 1) / current_monitor[1]

            # Downscale the pixel to match the pixmap
            x = int(pixel[0] * width_multiplier)
            y = int(pixel[1] * height_multiplier)
            unique_pixels.add((x, y))

        # Send unique pixels to be drawn
        self.update_pixmap_pixels(*(Pixel(QtCore.QPoint(x, y), self.pixel_colour) for x, y in unique_pixels))

    def update_pixmap_pixels(self, *pixels: Pixel) -> None:
        """Update a specific pixel in the QImage and refresh the display."""
        self.ui.thumbnail.update_pixels(*pixels)

        # Queue commands if redrawing is paused
        # This allows them to be resubmitted after an update
        if self.pause_redraw:
            self.redraw_queue.extend(pixels)
        elif self.redraw_queue:
            redraw_queue, self.redraw_queue = self.redraw_queue, []
            self.ui.thumbnail.update_pixels(*redraw_queue)

    def update_thumbnail_size(self) -> None:
        """Set a new thumbnail size after the window has finished resizing."""
        if self.ui.thumbnail.freeze_scale():
            self.request_thumbnail(force=True)

    def delete_mouse(self) -> None:
        """Request deletion of mouse data for the current profile."""
        profile = self.ui.current_profile.currentData()

        msg = QtWidgets.QMessageBox(self)
        msg.setIcon(QtWidgets.QMessageBox.Icon.Warning)
        msg.setWindowTitle('Delete Keyboard Data')
        msg.setText(f'Are you sure you want to delete all mouse data for {profile}?\n'
                    'This involves the movement, click and scroll data.\n'
                    'It will not trigger an autosave, but it cannot be undone.')
        msg.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No)
        msg.setDefaultButton(QtWidgets.QMessageBox.StandardButton.No)
        msg.setEscapeButton(QtWidgets.QMessageBox.StandardButton.No)

        if msg.exec_() == QtWidgets.QMessageBox.StandardButton.Yes:
            self._delete_mouse_pressed = True
            self.handle_delete_button_visibility()
            self.component.send_data(ipc.DeleteMouseData(profile))
            self._unsaved_profiles.add(profile)
            self._redraw_profile_combobox()
            self.request_profile_data(profile)

    def delete_keyboard(self) -> None:
        """Request deletion of keyboard data for the current profile."""
        profile = self.ui.current_profile.currentData()

        msg = QtWidgets.QMessageBox(self)
        msg.setIcon(QtWidgets.QMessageBox.Icon.Warning)
        msg.setWindowTitle('Delete Keyboard Data')
        msg.setText(f'Are you sure you want to delete all keyboard data for {profile}?\n'
                    'It will not trigger an autosave, but it cannot be undone.')
        msg.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No)
        msg.setDefaultButton(QtWidgets.QMessageBox.StandardButton.No)
        msg.setEscapeButton(QtWidgets.QMessageBox.StandardButton.No)

        if msg.exec_() == QtWidgets.QMessageBox.StandardButton.Yes:
            self._delete_keyboard_pressed = True
            self.handle_delete_button_visibility()
            self.component.send_data(ipc.DeleteKeyboardData(profile))
            self._unsaved_profiles.add(profile)
            self._redraw_profile_combobox()
            self.request_profile_data(profile)

    def delete_gamepad(self) -> None:
        """Request deletion of gamepad data for the current profile."""
        profile = self.ui.current_profile.currentData()

        msg = QtWidgets.QMessageBox(self)
        msg.setIcon(QtWidgets.QMessageBox.Icon.Warning)
        msg.setWindowTitle('Delete Keyboard Data')
        msg.setText(f'Are you sure you want to delete all gamepad data for {profile}?\n'
                    'This involves both the buttons and the thumbstick maps.\n'
                    'It will not trigger an autosave, but it cannot be undone.')
        msg.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No)
        msg.setDefaultButton(QtWidgets.QMessageBox.StandardButton.No)
        msg.setEscapeButton(QtWidgets.QMessageBox.StandardButton.No)

        if msg.exec_() == QtWidgets.QMessageBox.StandardButton.Yes:
            self._delete_gamepad_pressed = True
            self.handle_delete_button_visibility()
            self.component.send_data(ipc.DeleteGamepadData(profile))
            self._unsaved_profiles.add(profile)
            self._redraw_profile_combobox()
            self.request_profile_data(profile)

    def delete_network(self) -> None:
        """Request deletion of network data for the current profile."""
        profile = self.ui.current_profile.currentData()

        msg = QtWidgets.QMessageBox(self)
        msg.setIcon(QtWidgets.QMessageBox.Icon.Warning)
        msg.setWindowTitle('Delete Network Data')
        msg.setText(f'Are you sure you want to delete all upload and download data for {profile}?\n'
                    'It will not trigger an autosave, but it cannot be undone.')
        msg.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No)
        msg.setDefaultButton(QtWidgets.QMessageBox.StandardButton.No)
        msg.setEscapeButton(QtWidgets.QMessageBox.StandardButton.No)

        if msg.exec_() == QtWidgets.QMessageBox.StandardButton.Yes:
            self._delete_network_pressed = True
            self.handle_delete_button_visibility()
            self.component.send_data(ipc.DeleteNetworkData(profile))
            self._unsaved_profiles.add(profile)
            self._redraw_profile_combobox()
            self.request_profile_data(profile)

    @QtCore.Slot(QtCore.Qt.CheckState)
    def toggle_profile_mouse_tracking(self, state: QtCore.Qt.CheckState) -> None:
        if not self.ui.track_mouse.isEnabled():
            return

        selected_profile = self.ui.current_profile.currentData()
        enable = state == QtCore.Qt.CheckState.Checked.value
        self.component.send_data(ipc.SetProfileMouseTracking(selected_profile, enable))

    @QtCore.Slot(QtCore.Qt.CheckState)
    def toggle_profile_keyboard_tracking(self, state: QtCore.Qt.CheckState) -> None:
        if not self.ui.track_keyboard.isEnabled():
            return

        selected_profile = self.ui.current_profile.currentData()
        enable = state == QtCore.Qt.CheckState.Checked.value
        self.component.send_data(ipc.SetProfileKeyboardTracking(selected_profile, enable))

    @QtCore.Slot(QtCore.Qt.CheckState)
    def toggle_profile_gamepad_tracking(self, state: QtCore.Qt.CheckState) -> None:
        if not self.ui.track_gamepad.isEnabled():
            return

        selected_profile = self.ui.current_profile.currentData()
        enable = state == QtCore.Qt.CheckState.Checked.value
        self.component.send_data(ipc.SetProfileGamepadTracking(selected_profile, enable))

    @QtCore.Slot(QtCore.Qt.CheckState)
    def toggle_profile_network_tracking(self, state: QtCore.Qt.CheckState) -> None:
        if not self.ui.track_network.isEnabled():
            return

        selected_profile = self.ui.current_profile.currentData()
        enable = state == QtCore.Qt.CheckState.Checked.value
        self.component.send_data(ipc.SetProfileNetworkTracking(selected_profile, enable))

    def handle_delete_button_visibility(self, _: Any = None) -> None:
        """Toggle the delete button visibility.

        They are only enabled when tracking is disabled, and when
        processing is not waiting to delete. Deleting a profile is only
        allowed once all tracking is disabled as a safety measure.
        """
        delete_mouse = self.ui.track_mouse.isEnabled() and not self.ui.track_mouse.isChecked() and not self._delete_mouse_pressed
        delete_keyboard = self.ui.track_keyboard.isEnabled() and not self.ui.track_keyboard.isChecked() and not self._delete_keyboard_pressed
        delete_gamepad = self.ui.track_gamepad.isEnabled() and not self.ui.track_gamepad.isChecked() and not self._delete_gamepad_pressed
        delete_network = self.ui.track_network.isEnabled() and not self.ui.track_network.isChecked() and not self._delete_network_pressed

        self.ui.delete_mouse.setEnabled(delete_mouse)
        self.ui.delete_keyboard.setEnabled(delete_keyboard)
        self.ui.delete_gamepad.setEnabled(delete_gamepad)
        self.ui.delete_network.setEnabled(delete_network)
        self.ui.delete_profile.setEnabled(delete_mouse and delete_keyboard and delete_gamepad and delete_network)

    @QtCore.Slot(bool)
    def set_autorun(self, value: bool) -> None:
        """Set if the application runs on startup.
        This only works on the built executable as it adds it to the
        registry. If the executable is moved then it will need to be
        re-added.
        """
        AutoRun()(value)
        self.notify(f'{self.windowTitle()} will {"now" if value else "no longer"} launch when Windows starts.')

    @QtCore.Slot(bool)
    def set_minimise_on_start(self, value: bool) -> None:
        """Set if the app should minimise on startup.
        This saves a config value which is read the next time it loads.
        """
        self.config.minimise_on_start = value
        self.config.save()

    @QtCore.Slot(bool)
    def toggle_console(self, show: bool) -> None:
        """Show or hide the console."""
        self.component.send_data(ipc.ToggleConsole(show))

    @QtCore.Slot(bool)
    def toggle_full_screen(self, full_screen: bool) -> None:
        """Set or unset the full screen view."""
        if full_screen:
            self.showFullScreen()
        else:
            self.showNormal()
        self.ui.statusbar.setVisible(not full_screen)
        self.ui.menubar.setVisible(not full_screen)
        self.ui.save_render.setVisible(not full_screen)
        self.ui.horizontal_splitter.setSizes([1, int(not full_screen)])

        self.ui.main_layout.setContentsMargins(QtCore.QMargins(0, 0, 0, 0) if full_screen else self._margins_main)
        self.ui.render_layout.setContentsMargins(QtCore.QMargins(0, 0, 0, 0) if full_screen else self._margins_render)

    def notify(self, message: str) -> None:
        """Show a notification.
        If the tray messages are not available, a popup will be shown.
        """
        if self.tray is None or not self.tray.supportsMessages():
            msg = QtWidgets.QMessageBox(self)
            msg.setWindowTitle(self.windowTitle())
            msg.setIcon(QtWidgets.QMessageBox.Icon.Information)
            msg.setText(message)
            msg.exec_()
        else:
            self.tray.showMessage(self.windowTitle(), message, self.tray.icon(), 2000)
