from __future__ import annotations

import os
import math
import random
import re
import sys
import time
import webbrowser
from contextlib import suppress
from dataclasses import dataclass, field
from pathlib import Path
from typing import cast, Any, Generic, Iterable, TypeVar, TYPE_CHECKING

from PIL import Image
from PySide6 import QtCore, QtWidgets, QtGui

from .about import AboutWindow
from .applist import AppListWindow
from .ui import layout
from .utils import format_distance, format_ticks, format_bytes, format_network_speed, ICON_PATH
from .widgets import Pixel, AutoCloseMessageBox
from ..components import ipc
from ..constants import SYS_EXECUTABLE
from ..config.cli import CLI
from ..config.settings import GlobalConfig
from ..constants import COMPRESSION_FACTOR, COMPRESSION_THRESHOLD, DEFAULT_PROFILE_NAME, RADIAL_ARRAY_SIZE
from ..constants import UPDATES_PER_SECOND, IS_EXE, TRACKING_DISABLE
from ..file import PROFILE_DIR, get_profile_names, get_filename
from ..legacy import colours
from ..update import is_latest_version
from ..utils import keycodes, get_cursor_pos
from ..utils.math import calculate_line, calculate_distance, calculate_pixel_offset
from ..utils.system import monitor_locations, check_autostart, set_autostart, remove_autostart

if TYPE_CHECKING:
    from ..components.gui import GUI


T = TypeVar('T')


def _get_docs_folder() -> Path:
    """Get the documents folder."""
    return Path(QtCore.QStandardPaths.writableLocation(QtCore.QStandardPaths.StandardLocation.DocumentsLocation))


@dataclass
class MapData:
    position: tuple[int, int] | None = field(default_factory=get_cursor_pos)
    distance: float = field(default=0.0)
    counter: int = field(default=0)


@dataclass
class Profile:
    """Hold data related to the currently running profile."""

    name: str
    rects: list[tuple[int, int, int, int]] = field(default_factory=list)
    track_mouse: bool = True
    track_keyboard: bool = True
    track_gamepad: bool = True
    track_network: bool = True


@dataclass
class RenderOption(Generic[T]):
    """Store different values per render type."""

    movement: T
    speed: T
    heatmap: T
    keyboard: T

    def get(self, render_type: ipc.RenderType) -> T:
        """Get the value for a render type."""
        match render_type:
            case (ipc.RenderType.Time | ipc.RenderType.Thumbstick_Time):
                return self.movement
            case ipc.RenderType.Speed | ipc.RenderType.Thumbstick_Speed:
                return self.speed
            case (ipc.RenderType.SingleClick | ipc.RenderType.DoubleClick | ipc.RenderType.HeldClick
                  | ipc.RenderType.Thumbstick_Heatmap | ipc.RenderType.TimeHeatmap):
                return self.heatmap
            case ipc.RenderType.Keyboard:
                return self.keyboard
            case _:
                raise NotImplementedError(f'Unsupported render type: {render_type}')

    def set(self, render_type: ipc.RenderType, value: T) -> None:
        """Set the value for a render type."""
        match render_type:
            case (ipc.RenderType.Time | ipc.RenderType.Thumbstick_Time):
                self.movement = value
            case ipc.RenderType.Speed | ipc.RenderType.Thumbstick_Speed:
                self.speed = value
            case (ipc.RenderType.SingleClick | ipc.RenderType.DoubleClick | ipc.RenderType.HeldClick
                  | ipc.RenderType.Thumbstick_Heatmap | ipc.RenderType.TimeHeatmap):
                self.heatmap = value
            case ipc.RenderType.Keyboard:
                self.keyboard = value
            case _:
                raise NotImplementedError(f'Unsupported render type: {render_type}')



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
        self._last_save_time = self._last_thumbnail_time = self._last_app_reload_time = int(time.time() * 10)
        self._delete_mouse_pressed = False
        self._delete_keyboard_pressed = False
        self._delete_gamepad_pressed = False
        self._delete_network_pressed = False
        self._profile_names = get_profile_names()
        self._unsaved_profiles: set[str] = set()
        self._redrawing_profiles = False
        self._is_loading_profile = 0
        self._is_closing = False
        self._is_changing_state = False
        self._pixel_colour_cache: dict[str, QtGui.QColor | None] = {}
        self._is_setting_click_state = False
        self._force_close = False
        self._waiting_on_save = False
        self._last_save_message: ipc.SaveComplete | None
        self.state = ipc.TrackingState.Paused

        # Set default render values
        self._render_colour = RenderOption('Ice', 'Ice', 'Jet', 'Aqua')
        self._contrast = RenderOption(1.0, 1.0, 1.0, 1.0)
        self._sampling = RenderOption(4, 4, 4, 4)
        self._sampling_preview = RenderOption(0, 0, 1, 1)
        self._padding = RenderOption(0, 0, 0, 0)
        self._clipping = RenderOption(0.0, 0.0, 0.001, 0.0)
        self._blur = RenderOption(0.0, 0.0, 0.0125, 0.0)
        self._linear = RenderOption(False, True, True, False)

        # Setup UI
        self.ui = layout.Ui_MainWindow()
        self.ui.setupUi(self)

        # Set initial widget states
        self.ui.statusbar.setVisible(False)
        self.ui.output_logs.setVisible(False)
        self.ui.record_history.setVisible(False)
        self.ui.tray_context_menu.menuAction().setVisible(False)
        self.ui.prefs_autostart.setChecked(check_autostart())
        self.ui.prefs_automin.setChecked(self.config.minimise_on_start)
        self.ui.prefs_console.setChecked(not IS_EXE)
        self.ui.prefs_track_mouse.setChecked(self.config.track_mouse)
        self.ui.prefs_track_keyboard.setChecked(self.config.track_keyboard)
        self.ui.prefs_track_gamepad.setChecked(self.config.track_gamepad)
        self.ui.prefs_track_network.setChecked(self.config.track_network)
        self.ui.contrast.setMaximum(float('inf'))

        # Cache buddies
        self._buddies: dict[QtWidgets.QWidget, QtWidgets.QLabel] = {}
        for label in cast(Iterable[QtWidgets.QLabel], self.findChildren(QtWidgets.QLabel)):
            buddy = label.buddy()
            if buddy is not None:
                self._buddies[buddy] = label

        # Copy tooltips to labels
        # This is done by adding an `inherit_tooltip` property
        for widget in cast(Iterable[QtWidgets.QWidget], self.findChildren(QtWidgets.QWidget)):
            tooltip = widget.toolTip()
            if not tooltip.startswith('!inherit'):
                continue
            inherits_from = tooltip.split(' ')[1]
            source_widget: QtWidgets.QWidget | None = self.findChild(QtWidgets.QWidget, inherits_from)
            if source_widget is not None:
                widget.setToolTip(source_widget.toolTip())

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
            self.tray.activated.connect(self.tray_activated)
            self.tray.show()
        else:
            self.tray = None
            self.ui.menu_allow_minimise.setChecked(False)
            self.ui.menu_allow_minimise.setEnabled(False)

        self.current_profile = Profile(DEFAULT_PROFILE_NAME)
        #self.update_profile_combobox(DEFAULT_PROFILE_NAME)

        # self.ui.map_type = QtWidgets.QComboBox()
        self.ui.map_type.addItem('[Mouse] Movement', ipc.RenderType.Time)
        self.ui.map_type.addItem('[Mouse] Speed', ipc.RenderType.Speed)
        self.ui.map_type.addItem('[Mouse] Position', ipc.RenderType.TimeHeatmap)
        self.ui.map_type.addItem('[Mouse] Clicks', ipc.RenderType.SingleClick)
        self.ui.map_type.addItem('[Mouse] Double Clicks', ipc.RenderType.DoubleClick)
        self.ui.map_type.addItem('[Mouse] Held Clicks', ipc.RenderType.HeldClick)
        self.ui.map_type.addItem('[Keyboard] Key Presses', ipc.RenderType.Keyboard)
        self.ui.map_type.addItem('[Thumbsticks] Movement', ipc.RenderType.Thumbstick_Time)
        self.ui.map_type.addItem('[Thumbsticks] Speed', ipc.RenderType.Thumbstick_Speed)
        self.ui.map_type.addItem('[Thumbsticks] Position', ipc.RenderType.Thumbstick_Heatmap)

        self.cursor_data = MapData(get_cursor_pos())
        self.thumbstick_l_data = MapData((0, 0))
        self.thumbstick_r_data = MapData((0, 0))

        self.mouse_click_count = self.mouse_held_count = self.mouse_scroll_count = 0
        self.button_press_count = self.key_press_count = 0
        self.elapsed_time = self.active_time = self.inactive_time = 0
        self.monitor_data = monitor_locations()
        self.render_type = ipc.RenderType.Time
        self.tick_current = 0
        self.last_render: tuple[ipc.RenderType, int] = (self.render_type, -1)
        self.save_all_request_sent = self.save_profile_request_sent = False
        self._bytes_sent = self.bytes_sent = 0
        self._bytes_recv = self.bytes_recv = 0

        self.timer_activity = QtCore.QTimer(self)
        self._timer_thumbnail_update = QtCore.QTimer(self)
        self._timer_thumbnail_update.setSingleShot(True)
        self._timer_resize = QtCore.QTimer(self)
        self._timer_resize.setSingleShot(True)
        self._timer_rendering = QtCore.QTimer(self)
        self._timer_rendering.setSingleShot(True)

        # Connect signals and slots
        self.ui.menu_exit.triggered.connect(self.shut_down)
        self.ui.file_tracking_start.triggered.connect(self.start_tracking)
        self.ui.file_tracking_pause.triggered.connect(self.pause_tracking)
        self.ui.save_render.clicked.connect(self.request_render)
        self.ui.current_profile.currentIndexChanged.connect(self.profile_changed)
        self.ui.map_type.currentIndexChanged.connect(self.render_type_changed)
        self.ui.show_left_clicks.toggled.connect(self.show_clicks_changed)
        self.ui.show_middle_clicks.toggled.connect(self.show_clicks_changed)
        self.ui.show_right_clicks.toggled.connect(self.show_clicks_changed)
        self.ui.show_count.toggled.connect(self.show_count_changed)
        self.ui.show_time.toggled.connect(self.show_time_changed)
        self.ui.sampling.valueChanged.connect(self.sampling_changed)
        self.ui.colour_option.currentTextChanged.connect(self.render_colour_changed)
        self.ui.auto_switch_profile.stateChanged.connect(self.toggle_auto_switch_profile)
        self.ui.thumbnail_refresh.clicked.connect(self.request_thumbnail)
        self.ui.thumbnail.resized.connect(self.thumbnail_resize)
        self.ui.thumbnail.clicked.connect(self.thumbnail_click)
        self.ui.padding.valueChanged.connect(self.padding_changed)
        self.ui.contrast.valueChanged.connect(self.contrast_changed)
        self.ui.clipping.valueChanged.connect(self.clipping_changed)
        self.ui.blur.valueChanged.connect(self.blur_changed)
        self.ui.linear.toggled.connect(self.linear_changed)
        self.ui.lock_aspect.stateChanged.connect(self.lock_aspect_changed)
        self.ui.custom_width.valueChanged.connect(self.render_resolution_value_changed)
        self.ui.custom_height.valueChanged.connect(self.render_resolution_value_changed)
        self.ui.enable_custom_width.stateChanged.connect(self.custom_width_toggle)
        self.ui.enable_custom_height.stateChanged.connect(self.custom_height_toggle)
        self.ui.thumbnail_sampling.valueChanged.connect(self.sampling_preview_changed)
        self.ui.interpolation_order.valueChanged.connect(self.interpolation_order_changed)
        self.ui.applist_reload.clicked.connect(self.reload_applist)
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
        self.ui.delete_profile.clicked.connect(self.delete_profile)
        self.ui.autosave.stateChanged.connect(self.toggle_autosave)
        self.ui.file_save.triggered.connect(self.manual_save_all)
        self.ui.profile_save.clicked.connect(self.manual_save_profile)
        self.ui.tray_show.triggered.connect(self.load_from_tray)
        self.ui.tray_hide.triggered.connect(self.hide_to_tray)
        self.ui.tray_exit.triggered.connect(self.shut_down)
        self.ui.prefs_autostart.triggered.connect(self.set_autostart)
        self.ui.prefs_automin.triggered.connect(self.set_minimise_on_start)
        self.ui.prefs_console.triggered.connect(self.toggle_console)
        self.ui.always_on_top.triggered.connect(self.set_always_on_top)
        self.ui.show_advanced.toggled.connect(self.toggle_advanced_options)
        self.ui.prefs_track_mouse.triggered.connect(self.set_mouse_tracking_enabled)
        self.ui.prefs_track_keyboard.triggered.connect(self.set_keyboard_tracking_enabled)
        self.ui.prefs_track_gamepad.triggered.connect(self.set_gamepad_tracking_enabled)
        self.ui.prefs_track_network.triggered.connect(self.set_network_tracking_enabled)
        self.ui.full_screen.triggered.connect(self.toggle_full_screen)
        self.ui.file_import.triggered.connect(self.import_legacy_profile)
        self.ui.export_mouse_stats.triggered.connect(self.export_mouse_stats)
        self.ui.export_keyboard_stats.triggered.connect(self.export_keyboard_stats)
        self.ui.export_gamepad_stats.triggered.connect(self.export_gamepad_stats)
        self.ui.export_network_stats.triggered.connect(self.export_network_stats)
        self.ui.export_daily_stats.triggered.connect(self.export_daily_stats)
        self.ui.multi_monitor.toggled.connect(self.multi_monitor_change)
        self.ui.opts_monitor.toggled.connect(self.multi_monitor_override_toggle)
        self.ui.stat_app_add.clicked.connect(self.add_application)
        self.ui.link_facebook.triggered.connect(self.open_url)
        self.ui.link_github.triggered.connect(self.open_url)
        self.ui.link_reddit.triggered.connect(self.open_url)
        self.ui.link_donate.triggered.connect(self.open_url)
        self.ui.about.triggered.connect(self.about)
        self.ui.tip.linkActivated.connect(webbrowser.open)
        self.timer_activity.timeout.connect(self.update_activity_preview)
        self.timer_activity.timeout.connect(self.update_time_since_save)
        self.timer_activity.timeout.connect(self.update_time_since_thumbnail)
        self.timer_activity.timeout.connect(self.update_time_since_applist_reload)
        self.timer_activity.timeout.connect(self.update_queue_size)
        self._timer_thumbnail_update.timeout.connect(self._request_thumbnail)
        self._timer_resize.timeout.connect(self.update_thumbnail_size)
        self._timer_rendering.timeout.connect(self.ui.thumbnail.show_rendering_text)

        self.ui.debug_state_running.triggered.connect(self.start_tracking)
        self.ui.debug_state_paused.triggered.connect(self.pause_tracking)
        self.ui.debug_state_stopped.triggered.connect(self.stop_tracking)
        self.ui.debug_raise_app.triggered.connect(self.raise_app_detection)
        self.ui.debug_raise_tracking.triggered.connect(self.raise_tracking)
        self.ui.debug_raise_processing.triggered.connect(self.raise_processing)
        self.ui.debug_raise_gui.triggered.connect(self.raise_gui)
        self.ui.debug_raise_hub.triggered.connect(self.raise_hub)

        # Trigger initial setup
        self.profile_changed(0)
        self.ui.show_advanced.setChecked(False)

        # Set tip
        tips = ['tip_tracking']
        if not is_latest_version():
            tips.append('tip_update')
        self.ui.tip.setText(f'Tip: {self.ui.tip.property(random.choice(tips))}')

    @QtCore.Slot()
    def open_url(self) -> None:
        """Open a URL from the selected action.
        Requires the action to have a "website" property.
        """
        action= cast(QtGui.QAction, self.sender())
        url: QtCore.QUrl = action.property('website')
        webbrowser.open(url.toString())

    @QtCore.Slot()
    def about(self) -> None:
        """Load the "about" window."""
        win = AboutWindow(self)
        win.exec()

    @property
    def pixel_colour(self) -> QtGui.QColor:
        """Get the pixel colour to draw with."""
        colour_map = self.render_colour
        if colour_map not in self._pixel_colour_cache:
            try:
                generated_map = colours.calculate_colour_map(self.render_colour)

            # This is legacy code with bad error handling
            # If any error occurs, just show a transparent image
            except Exception:
                self._pixel_colour_cache[colour_map] = None

            else:
                self._pixel_colour_cache[colour_map] = QtGui.QColor(*generated_map[-1])

        colour = self._pixel_colour_cache[colour_map]
        if colour is None:
            return QtGui.QColor(QtCore.Qt.GlobalColor.transparent)
        return colour

    @property
    def render_type(self) -> ipc.RenderType:
        """Get the render type."""
        return self._render_type

    @render_type.setter
    def render_type(self, render_type: ipc.RenderType) -> None:
        """Set the render type.
        This populates the available colour maps.
        """
        self._render_type = render_type

        # Add items to render colour input
        self.pause_colour_change = True

        self.ui.colour_option.clear()

        colour_maps = colours.get_map_matches(
            tracks=render_type in (ipc.RenderType.Time, ipc.RenderType.Speed,
                                   ipc.RenderType.Thumbstick_Time, ipc.RenderType.Thumbstick_Speed),
            clicks=render_type in (ipc.RenderType.SingleClick, ipc.RenderType.DoubleClick, ipc.RenderType.HeldClick,
                                   ipc.RenderType.Thumbstick_Heatmap, ipc.RenderType.TimeHeatmap),
            keyboard=render_type == ipc.RenderType.Keyboard,
        )
        self.ui.colour_option.addItems(sorted(colour_maps))

        # Set it back to the previous colour selection
        if (idx := self.ui.colour_option.findText(self.render_colour)) == -1:
            self.ui.colour_option.setCurrentText(self.render_colour)
        else:
            self.ui.colour_option.setCurrentIndex(idx)

        # Load in other settings
        self.ui.contrast.setValue(self.contrast)
        self.ui.sampling.setValue(self.sampling)
        self.ui.thumbnail_sampling.setValue(self.sampling_preview)
        self.ui.padding.setValue(self.padding)
        self.ui.clipping.setValue(self.clipping)
        self.ui.blur.setValue(self.blur)
        self.ui.linear.setChecked(self.linear)
        self.toggle_advanced_options(self.ui.show_advanced.isChecked())

        self.pause_colour_change = False

    @property
    def render_colour(self) -> str:
        """Get the render colour for the current render type."""
        return self._render_colour.get(self.render_type)

    @render_colour.setter
    def render_colour(self, colour: str) -> None:
        """Set the render colour for the current render type.
        This will update the current pixel colour too.
        """
        self._render_colour.set(self.render_type, colour)

    @property
    def contrast(self) -> float:
        """Get the contrast for the current render type."""
        return self._contrast.get(self.render_type)

    @contrast.setter
    def contrast(self, value: float) -> None:
        """Set a new constrast value for the current render type."""
        self._contrast.set(self.render_type, value)

    @property
    def sampling(self) -> int:
        """Get the sampling for the current render type."""
        return self._sampling.get(self.render_type)

    @sampling.setter
    def sampling(self, value: int) -> None:
        """Set a new sampling value for the current render type."""
        self._sampling.set(self.render_type, value)

    @property
    def sampling_preview(self) -> int:
        """Get the thumbnail sampling for the current render type."""
        return self._sampling_preview.get(self.render_type)

    @sampling_preview.setter
    def sampling_preview(self, value: int) -> None:
        """Set a new thumbnail sampling value for the current render type."""
        self._sampling_preview.set(self.render_type, value)

    @property
    def padding(self) -> int:
        """Get the padding for the current render type."""
        return self._padding.get(self.render_type)

    @padding.setter
    def padding(self, value: int) -> None:
        """Set a new padding value for the current render type."""
        self._padding.set(self.render_type, value)

    @property
    def clipping(self) -> float:
        """Get the clipping for the current render type."""
        return self._clipping.get(self.render_type)

    @clipping.setter
    def clipping(self, value: float) -> None:
        """Set a new clipping value for the current render type."""
        self._clipping.set(self.render_type, value)

    @property
    def blur(self) -> float:
        """Get the blur for the current render type."""
        return self._blur.get(self.render_type)

    @blur.setter
    def blur(self, value: float) -> None:
        """Set a new blur value for the current render type."""
        self._blur.set(self.render_type, value)

    @property
    def linear(self) -> bool:
        """Get if linear mapping is enabled for the current render type."""
        return self._linear.get(self.render_type)

    @linear.setter
    def linear(self, value: bool) -> None:
        """Set if linear mapping is enabled for the current render type."""
        self._linear.set(self.render_type, value)

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
    def save_all_request_sent(self) -> bool:
        """If waiting on a save request."""
        return self._save_all_request_sent

    @save_all_request_sent.setter
    def save_all_request_sent(self, value: bool) -> None:
        """Set when waiting on a save request.
        This blocks the save action from triggering.
        """
        self._save_all_request_sent = value
        self.ui.save.setEnabled(not value)
        self.ui.file_save.setEnabled(not value)

    @property
    def save_profile_request_sent(self) -> bool:
        """If waiting on a save request."""
        return self._save_profile_request_sent

    @save_profile_request_sent.setter
    def save_profile_request_sent(self, value: bool) -> None:
        """Set when waiting on a save request.
        This blocks the save action from triggering.
        """
        self._save_profile_request_sent = value
        self.ui.profile_save.setEnabled(not value)

    @property
    def resolutions(self) -> dict[tuple[int, int], tuple[int, bool]]:
        """Get the resolution data for the profile."""
        return self._resolutions

    @resolutions.setter
    def resolutions(self, resolutions: dict[tuple[int, int], tuple[int, bool]]) -> None:
        """Load in the resolution data."""
        self._resolutions = resolutions

        # Delete all existing items in the layout
        layout = self.ui.profile_resolutions.layout()
        while layout.count():
            item = self.ui.profile_resolutions.layout().takeAt(0)
            item.widget().deleteLater()

        # Populate with new widgets
        total_count = sum(count for count, enabled in resolutions.values())
        sorted_items = sorted(resolutions.items(), key=lambda kv: kv[1][0], reverse=True)
        for row, ((width, height), (count, enabled)) in enumerate(sorted_items):
            checkbox = QtWidgets.QCheckBox(f'{width}x{height}')
            checkbox.setChecked(enabled)
            checkbox.setToolTip(f'Toggle rendering of data recorded at {width}x{height}.')
            checkbox.toggled.connect(self.resolution_toggled)
            label = QtWidgets.QLabel(f'{round(100 * count / total_count, 3)}%')
            label.setToolTip('The percentage of time this resolution has been tracked.\n'
                             '\n'
                             f'Raw value: {count}')
            layout.addWidget(checkbox, row, 0)
            layout.addWidget(label, row, 1)

    @QtCore.Slot(bool)
    def resolution_toggled(self, value: bool) -> None:
        """Toggle rendering of a particular resolution in a profile."""
        checkbox = cast(QtWidgets.QCheckBox, self.sender())
        profile = self.ui.current_profile.currentData()
        width, height = map(int, checkbox.text().split('x'))
        self.component.send_data(ipc.ToggleProfileResolution(profile, (width, height), value))
        self.mark_profiles_unsaved(profile)
        self.request_thumbnail()

    @QtCore.Slot()
    def multi_monitor_change(self) -> None:
        """Change the multiple monitor option."""
        if not self.ui.opts_monitor.isChecked():
            return
        profile = self.ui.current_profile.currentData()
        self.component.send_data(ipc.ToggleProfileMultiMonitor(profile, self.ui.multi_monitor.isChecked()))

    @QtCore.Slot(bool)
    def multi_monitor_override_toggle(self, checked: bool) -> None:
        """Enable or disable the multi monitor override."""
        if not self.ui.opts_monitor.isEnabled():
            return
        profile = self.ui.current_profile.currentData()
        self.component.send_data(ipc.ToggleProfileMultiMonitor(profile, self.ui.multi_monitor.isChecked() if checked else None))

    @QtCore.Slot()
    def update_activity_preview(self) -> None:
        """Update the activity preview periodically.
        The updates are too frequent to do per tick.
        """
        active_time = self.active_time
        inactive_time = self.inactive_time

        # The active and inactive time don't update every tick
        # Add the difference to keep the GUI in sync
        inactivity_threshold = UPDATES_PER_SECOND * GlobalConfig.inactivity_time
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
        text = format_ticks(time.time() * 10 - self._last_save_time, 10, 1)
        self.ui.time_since_save.setText(text)

    @QtCore.Slot()
    def update_time_since_thumbnail(self) -> None:
        """Set how long it has been since the last thumbnail render."""
        text = format_ticks(time.time() * 10 - self._last_thumbnail_time, 10, 1)
        self.ui.time_since_thumbnail.setText(text)

    @QtCore.Slot()
    def update_time_since_applist_reload(self) -> None:
        """Set how long it has been since the last thumbnail render."""
        text = format_ticks(time.time() * 10 - self._last_app_reload_time, 10, 1)
        self.ui.time_since_applist_reload.setText(text)

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

        # Update the profile order by removing the record and inserting it at the top
        name_lower = profile.name.lower()
        for i, name in enumerate(map(str.lower, self._profile_names)):
            if name == name_lower:
                del self._profile_names[i]
                break

        self._profile_names.insert(0, profile.name)
        self.mark_profiles_unsaved(profile.name)
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
    def manual_save_all(self) -> None:
        """Trigger a manual save request for all profiles."""
        if self.save_all_request_sent:
            return
        self.save_all_request_sent = True
        self.component.send_data(ipc.Save())

    @QtCore.Slot()
    def manual_save_profile(self) -> None:
        """Trigger a manual save request for a profile."""
        if self.save_profile_request_sent:
            return
        self.save_profile_request_sent = True
        self.component.send_data(ipc.Save(self.ui.current_profile.currentData()))

    @QtCore.Slot(QtCore.Qt.CheckState)
    def toggle_autosave(self, state: QtCore.Qt.CheckState) -> None:
        """Enable or disable autosaving."""
        self.component.send_data(ipc.Autosave(state == QtCore.Qt.CheckState.Checked.value))

    @QtCore.Slot(int)
    def profile_changed(self, idx: int) -> None:
        """Change the profile and trigger a redraw."""
        profile_name = self.ui.current_profile.itemData(idx)

        if not self._redrawing_profiles:
            self.request_profile_data(profile_name)
            if idx:
                self.ui.auto_switch_profile.setChecked(False)
            self.set_profile_modified_text()

    def request_profile_data(self, profile_name: str) -> None:
        """Request loading profile data."""
        self.component.send_data(ipc.ProfileDataRequest(profile_name))

        # Pause the signals on the track options
        if not self._is_loading_profile:
            self.ui.track_mouse.setEnabled(False)
            self.ui.track_keyboard.setEnabled(False)
            self.ui.track_gamepad.setEnabled(False)
            self.ui.track_network.setEnabled(False)
            self.ui.opts_status.setEnabled(False)
            self.ui.opts_resolution.setEnabled(False)
            self.ui.opts_monitor.setEnabled(False)
            self.ui.opts_tracking.setEnabled(False)

        self._is_loading_profile += 1
        self.start_rendering_timer()

    @QtCore.Slot(int)
    def render_type_changed(self, idx: int) -> None:
        """Change the render type and trigger a redraw."""
        self.render_type = self.ui.map_type.itemData(idx)
        self.request_thumbnail()

    @QtCore.Slot(bool)
    def show_clicks_changed(self, enabled: bool) -> None:
        """Update the render when the click visibility options change.

        Using a shift click is a quick way to check/uncheck all options.
        If shift clicking on a checked option, all other options will be
        unchecked. If shift clicking on an unchecked option, then all
        options will be checked.
        """
        if self._is_setting_click_state:
            return
        self._is_setting_click_state = True

        modifiers = QtWidgets.QApplication.keyboardModifiers()
        shift_held = modifiers & QtCore.Qt.KeyboardModifier.ShiftModifier

        checkboxes = {
            self.ui.show_left_clicks,
            self.ui.show_middle_clicks,
            self.ui.show_right_clicks,
        }

        if shift_held:
            sender = cast(QtWidgets.QCheckBox, self.sender())
            checkboxes.discard(sender)
            if enabled:
                for checkbox in checkboxes:
                    checkbox.setChecked(True)
            else:
                for checkbox in checkboxes:
                    checkbox.setChecked(False)
                sender.setChecked(True)

        self.request_thumbnail()
        self._is_setting_click_state = False

    @QtCore.Slot(bool)
    def show_count_changed(self) -> None:
        """Trigger when the count radio button changes."""
        self.request_thumbnail()

    @QtCore.Slot(bool)
    def show_time_changed(self) -> None:
        """Trigger when the time radio button changes."""
        self.request_thumbnail()

    @QtCore.Slot(int)
    def sampling_changed(self, value: int) -> None:
        """Change the sampling."""
        if self.pause_colour_change:
            return
        self.sampling = value

    @QtCore.Slot(int)
    def sampling_preview_changed(self, value: int) -> None:
        """Update the render when the sampling is changed."""
        if self.pause_colour_change:
            return
        self.sampling_preview = value
        self.request_thumbnail()

    @QtCore.Slot(str)
    def render_colour_changed(self, colour: str) -> None:
        """Update the render when the colour is changed."""
        if self.pause_colour_change:
            return
        self.render_colour = colour
        self.request_thumbnail()

    @QtCore.Slot(int)
    def padding_changed(self, value: int) -> None:
        """Update the render when the padding is changed."""
        if self.pause_colour_change:
            return
        self.padding = value
        self.request_thumbnail()

    @QtCore.Slot(float)
    def contrast_changed(self, value: float) -> None:
        """Update the render when the contrast is changed."""
        if self.pause_colour_change:
            return
        self.contrast = value
        self.request_thumbnail()

    @QtCore.Slot(float)
    def clipping_changed(self, value: float) -> None:
        """Update the render when the clipping is changed."""
        if self.pause_colour_change:
            return
        self.clipping = value
        self.request_thumbnail()

    @QtCore.Slot(float)
    def blur_changed(self, value: float) -> None:
        """Update the render when the blur is changed."""
        if self.pause_colour_change:
            return
        self.blur = value
        self.request_thumbnail()

    @QtCore.Slot(bool)
    def linear_changed(self, value: bool) -> None:
        """Update the render when the linear mapping is changed."""
        if self.pause_colour_change:
            return
        self.linear = value
        self.request_thumbnail()

    @QtCore.Slot(QtCore.Qt.CheckState)
    def lock_aspect_changed(self, state: QtCore.Qt.CheckState) -> None:
        """Update the thumbnail when the aspect ratio is locked or unlocked."""
        self.request_thumbnail()

    @QtCore.Slot(int)
    def render_resolution_value_changed(self, value: int) -> None:
        """Update the thumbnail when a custom resolution is set."""
        if self.ui.custom_width.isEnabled() or self.ui.custom_height.isEnabled():
            self.request_thumbnail()

    @QtCore.Slot(QtCore.Qt.CheckState)
    def custom_width_toggle(self, state: QtCore.Qt.CheckState) -> None:
        """Update the thumbnail when custom width is toggled."""
        self.request_thumbnail()

        # Reset to current width
        if state == QtCore.Qt.CheckState.Unchecked.value:
            self.ui.custom_width.setValue(self.ui.thumbnail.size().width())

    @QtCore.Slot(QtCore.Qt.CheckState)
    def custom_height_toggle(self, state: QtCore.Qt.CheckState) -> None:
        """Update the thumbnail when custom height is toggled."""
        self.request_thumbnail()

        # Reset to current height
        if state == QtCore.Qt.CheckState.Unchecked.value:
            self.ui.custom_height.setValue(self.ui.thumbnail.size().height())

    @QtCore.Slot(int)
    def interpolation_order_changed(self, value: int) -> None:
        """Update the render when the interpolation order changes."""
        self.request_thumbnail()

    @QtCore.Slot(QtCore.Qt.CheckState)
    def toggle_auto_switch_profile(self, state: QtCore.Qt.CheckState) -> None:
        """Switch to the current profile when auto switch is checked."""
        if state == QtCore.Qt.CheckState.Checked.value:
            self.ui.current_profile.setCurrentIndex(0)

    def _monitor_offset(self, pixel: tuple[int, int]) -> tuple[tuple[int, int], tuple[int, int]] | None:
        """Detect which monitor the pixel is on."""
        monitor_data = self.monitor_data
        if self.current_profile.rects:
            monitor_data = self.current_profile.rects

        single_monitor = self.ui.single_monitor.isChecked() if self.ui.opts_monitor.isChecked() else CLI.single_monitor
        if single_monitor:
            x_min, y_min, x_max, y_max = monitor_data[0]
            for x1, y1, x2, y2 in monitor_data[1:]:
                x_min = min(x_min, x1)
                y_min = min(y_min, y1)
                x_max = max(x_max, x2)
                y_max = max(y_max, y2)
            result = calculate_pixel_offset(pixel[0], pixel[1], x_min, y_min, x_max, y_max)
            if result is not None:
                return result

        else:
            for x1, y1, x2, y2 in monitor_data:
                result = calculate_pixel_offset(pixel[0], pixel[1], x1, y1, x2, y2)
                if result is not None:
                    return result

        return None

    def start_rendering_timer(self) -> None:
        """Start the timer to display rendering text.

        If a render is not completed within 1 second, then text will be
        drawn to the preview to update the user.
        """
        if not self._timer_rendering.isActive():
            self._timer_rendering.start(1000)

    def add_application(self) -> None:
        """Load the window to add new tracked applications."""
        win = AppListWindow(self)
        if win.exec():
            self.reload_applist()

    @QtCore.Slot()
    def reload_applist(self) -> None:
        """Send a request to reload AppList.txt."""
        self.component.send_data(ipc.ReloadAppList())

    def request_thumbnail(self) -> bool:
        """Trigger a request to draw a thumbnail.
        This uses a timer to prevent multiple simulaneous requests at
        the same time.
        """
        # Block when minimised
        if not self.isVisible():
            return False

        self._timer_thumbnail_update.start(100)
        return True

    def _request_thumbnail(self) -> bool:
        """Send a request to draw a thumbnail.
        This will start pooling mouse move data to be redrawn after.
        """
        # Block when minimised
        if not self.isVisible():
            return False

        # Flag if drawing to prevent building up duplicate commands
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

        # Handle custom resolution
        custom_width = self.ui.custom_width.value()
        custom_height = self.ui.custom_height.value()
        use_custom_width = self.ui.custom_width.isEnabled()
        use_custom_height = self.ui.custom_height.isEnabled()
        lock_aspect = self.ui.lock_aspect.isChecked()
        if not lock_aspect and (use_custom_width or use_custom_height):

            # Set the aspect ratio to requested
            aspect_ratio = custom_width / custom_height
            if aspect_ratio > width / height:
                height = round(width / aspect_ratio)
            else:
                width = round(height * aspect_ratio)

        # Ensure resolutions aren't greater than requested
        if use_custom_width:
            width = min(width, custom_width)
        if use_custom_height:
            height = min(height, custom_height)

        self.component.send_data(ipc.RenderRequest(self.render_type,
                                                   width=width, height=height, lock_aspect=lock_aspect,
                                                   profile=profile, file_path=None,
                                                   colour_map=self.render_colour, padding=self.padding,
                                                   sampling=self.ui.thumbnail_sampling.value(),
                                                   contrast=self.contrast, clipping=self.clipping,
                                                   blur=self.blur, linear=self.linear,
                                                   show_left_clicks=self.ui.show_left_clicks.isChecked(),
                                                   show_middle_clicks=self.ui.show_middle_clicks.isChecked(),
                                                   show_right_clicks=self.ui.show_right_clicks.isChecked(),
                                                   show_count=self.ui.show_count.isChecked(),
                                                   show_time=self.ui.show_time.isChecked(),
                                                   interpolation_order=self.ui.interpolation_order.value()))
        return True

    @QtCore.Slot(QtCore.QSize)
    def thumbnail_resize(self, size: QtCore.QSize) -> None:
        """Start the resize timer when the thumbnail changes size.
        This prevents constant render requests as it will only trigger
        after resizing has finished.
        """
        self._timer_resize.start(100)

        if not self.ui.enable_custom_width.isChecked():
            self.ui.custom_width.setValue(size.width())
        if not self.ui.enable_custom_height.isChecked():
            self.ui.custom_height.setValue(size.height())

    @QtCore.Slot(bool)
    def thumbnail_click(self, state: bool) -> None:
        """Handle what to do when the thumbnail is clicked."""
        if state:
            self.notify(f'{self.windowTitle()} has resumed tracking.')
            self.start_tracking()
        else:
            self.notify(f'{self.windowTitle()} has paused tracking.')
            self.pause_tracking()

    def request_render(self) -> None:
        """Send a render request."""

        dialog = QtWidgets.QFileDialog()
        dialog.setAcceptMode(QtWidgets.QFileDialog.AcceptMode.AcceptSave)
        dialog.setNameFilters(['PNG Files (*.png)"'])
        dialog.setDefaultSuffix('png')

        match self.render_type:
            case ipc.RenderType.Time:
                name = 'Mouse Movement'
            case ipc.RenderType.TimeHeatmap:
                name = 'Mouse Position'
            case ipc.RenderType.Speed:
                name = 'Mouse Speed'
            case ipc.RenderType.SingleClick:
                name = 'Mouse Clicks'
            case ipc.RenderType.DoubleClick:
                name = 'Mouse Double Clicks'
            case ipc.RenderType.HeldClick:
                name = 'Mouse Held Clicks'
            case ipc.RenderType.Thumbstick_Time:
                name = 'Gamepad Thumbstick Movement'
            case ipc.RenderType.Thumbstick_Heatmap:
                name = 'Gamepad Thumbstick Position'
            case ipc.RenderType.Thumbstick_Speed:
                name = 'Gamepad Thumbstick Speed'
            case ipc.RenderType.Keyboard:
                name = 'Keyboard Heatmap'
            case _:
                name = 'Data'

        profile = self.ui.current_profile.currentData()
        profile_safe = re.sub(r'[^\w_.)( -]', '', profile)
        image_dir = Path.home() / 'Pictures'
        if image_dir.exists():
            image_dir /= 'MouseTracks'
            if not image_dir.exists():
                image_dir.mkdir()
        image_dir /= f'[{format_ticks(self.elapsed_time)}][{self.render_colour}] {profile_safe} - {name}.png'
        file_path, accept = dialog.getSaveFileName(None, 'Save Image', str(image_dir), 'Image Files (*.png)')

        if accept:
            width = self.ui.custom_width.value() if self.ui.custom_width.isEnabled() else None
            height = self.ui.custom_height.value() if self.ui.custom_height.isEnabled() else None
            self.component.send_data(ipc.RenderRequest(self.render_type,
                                                       width=width, height=height, lock_aspect=False,
                                                       profile=profile, file_path=file_path,
                                                       colour_map=self.render_colour, sampling=self.sampling,
                                                       padding=self.padding, contrast=self.contrast,
                                                       clipping=self.clipping, blur=self.blur, linear=self.linear,
                                                       show_left_clicks=self.ui.show_left_clicks.isChecked(),
                                                       show_middle_clicks=self.ui.show_middle_clicks.isChecked(),
                                                       show_right_clicks=self.ui.show_right_clicks.isChecked(),
                                                       show_count=self.ui.show_count.isChecked(),
                                                       show_time=self.ui.show_time.isChecked(),
                                                       interpolation_order=self.ui.interpolation_order.value()))

    def thumbnail_render_check(self) -> None:
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
        if count % math.ceil(update_frequency / GlobalConfig.preview_frequency_multiplier):
            return

        # Skip repeat renders
        if (self.render_type, count) == self.last_render:
            return

        # Skip if already rendering
        if self.pause_redraw:
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

            case ipc.TrackingStarted():
                self.state = ipc.TrackingState.Running
                self.ui.thumbnail.playback_overlay.playback_state = True

                self.request_thumbnail()
                self.ui.save.setEnabled(True)
                self.ui.thumbnail_refresh.setEnabled(True)
                self.ui.applist_reload.setEnabled(True)
                self.set_profile_modified_text()

            case ipc.PauseTracking():
                self.state = ipc.TrackingState.Paused
                self.ui.thumbnail.playback_overlay.playback_state = False

                self.ui.save.setEnabled(True)
                self.ui.thumbnail_refresh.setEnabled(True)
                self.ui.applist_reload.setEnabled(True)
                self.set_profile_modified_text()

            case ipc.StopTracking():
                self.state = ipc.TrackingState.Stopped
                self.ui.thumbnail.playback_overlay.playback_state = False

                self.ui.save.setEnabled(False)
                self.ui.thumbnail_refresh.setEnabled(False)
                self.ui.applist_reload.setEnabled(False)
                self.set_profile_modified_text()

            case ipc.Exit():
                self.shut_down(force=True)

            # When monitors change, store the new data
            case ipc.MonitorsChanged():
                self.monitor_data = message.data

            case ipc.Render():
                height, width, channels = message.array.shape
                failed = width == height == 0

                target_height = int(height / (message.request.sampling or 1))
                target_width = int(width / (message.request.sampling or 1))

                # Draw the new pixmap
                if message.request.file_path is None:
                    self._timer_rendering.stop()
                    self.ui.thumbnail.hide_rendering_text()

                    self._last_thumbnail_time = int(time.time() * 10)
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
                        scaled_image = image.scaled(target_width, target_height, QtCore.Qt.AspectRatioMode.KeepAspectRatio, QtCore.Qt.TransformationMode.SmoothTransformation)
                        self.ui.thumbnail.set_pixmap(scaled_image)

                    self.pause_redraw -= 1

                # Save a render
                elif failed:
                    msg = QtWidgets.QMessageBox(self)
                    msg.setWindowTitle('Render Failed')
                    msg.setIcon(QtWidgets.QMessageBox.Icon.Critical)
                    msg.setText('No data is available for this render.')
                    msg.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Ok)
                    msg.exec()

                else:
                    im = Image.fromarray(message.array)
                    im = im.resize((target_width, target_height), Image.Resampling.LANCZOS)
                    im.save(message.request.file_path)
                    os.startfile(message.request.file_path)

            case ipc.MouseHeld() if self.is_live and self.mouse_tracking_enabled:
                self.mouse_held_count += 1

            case ipc.MouseMove() if self.is_live and self.mouse_tracking_enabled:
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

            # Update the selected profile
            case ipc.CurrentProfileChanged():
                self.current_profile = Profile(message.name, message.rects)

                if self.is_live:
                    self.request_profile_data(message.name)

            case ipc.ApplicationFocusChanged():
                self.ui.stat_app_exe.setText(os.path.basename(message.exe))
                self.ui.stat_app_title.setText(message.title)
                self.ui.stat_app_tracked.setText('Yes' if message.tracked else 'No')

            # Show the correct distance
            case ipc.ProfileData():
                self._is_loading_profile -= 1
                self.ui.tab_options.setTabText(1, f'{message.profile_name} Options')

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
                self.resolutions = message.resolutions
                if message.multi_monitor is None:
                    single_monitor = CLI.single_monitor
                    multi_monitor = CLI.multi_monitor
                else:
                    single_monitor = not message.multi_monitor
                    multi_monitor = message.multi_monitor
                self.ui.single_monitor.setChecked(single_monitor)
                self.ui.multi_monitor.setChecked(multi_monitor)
                self.ui.opts_monitor.setChecked(message.multi_monitor is not None)

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
                # If disabled, ensure they are unchecked
                if CLI.disable_mouse:
                    self.ui.track_mouse.setChecked(False)
                else:
                    self.ui.track_mouse.setEnabled(not self._is_loading_profile)
                if CLI.disable_keyboard:
                    self.ui.track_keyboard.setChecked(False)
                else:
                    self.ui.track_keyboard.setEnabled(not self._is_loading_profile)
                if CLI.disable_gamepad:
                    self.ui.track_gamepad.setChecked(False)
                else:
                    self.ui.track_gamepad.setEnabled(not self._is_loading_profile)
                if CLI.disable_network:
                    self.ui.track_network.setChecked(False)
                else:
                    self.ui.track_network.setEnabled(not self._is_loading_profile)

                # Enable widgets and redraw when loading has finished
                if not self._is_loading_profile:
                    self.request_thumbnail()
                    self.ui.opts_status.setEnabled(True)
                    self.ui.opts_resolution.setEnabled(True)
                    self.ui.opts_monitor.setEnabled(True)
                    self.ui.opts_tracking.setEnabled(message.profile_name != TRACKING_DISABLE)

            case ipc.DataTransfer():
                if self.is_live and self.ui.track_network.isChecked():
                    self.bytes_sent += message.bytes_sent
                    self.bytes_recv += message.bytes_recv

                    self.ui.stat_download_current.setText(format_network_speed(message.bytes_recv))
                    self.ui.stat_upload_current.setText(format_network_speed(message.bytes_sent))

                else:
                    self.ui.stat_download_current.setText(format_network_speed(0))
                    self.ui.stat_upload_current.setText(format_network_speed(0))

            case ipc.SaveComplete():
                self._last_save_message = message
                self._last_save_time = int(time.time() * 10)
                self.mark_profiles_saved(*message.succeeded)
                self.mark_profiles_unsaved(self.current_profile.name)
                self._redraw_profile_combobox()

                # Notify when complete
                if self.save_all_request_sent:
                    self.save_all_request_sent = False

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

                if self.save_profile_request_sent:
                    self.save_profile_request_sent = False

                    msg = QtWidgets.QMessageBox(self)
                    msg.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Ok)

                    if message.failed:
                        msg.setWindowTitle('Save Failed')
                        msg.setIcon(QtWidgets.QMessageBox.Icon.Warning)
                        msg.setText(f'Profile "{message.failed[0]}" failed to save.')
                    elif message.succeeded:
                        msg.setWindowTitle('Successful')
                        msg.setIcon(QtWidgets.QMessageBox.Icon.Information)
                        msg.setText(f'Profile "{message.succeeded[0]}" has been saved.')
                    else:
                        raise RuntimeError('incorrect message format')

                    msg.exec()

                # Continue shutdown now save message has been received
                if self._is_closing:
                    self.shut_down(force=True)

            case ipc.DebugRaiseError():
                raise RuntimeError('[GUI] Test Exception')

            # Update the GUI with the component statuses
            case ipc.QueueSize():
                self.ui.stat_hub_queue.setText(str(message.hub))
                self.ui.stat_tracking_queue.setText(str(message.tracking))
                self.ui.stat_processing_queue.setText(str(message.processing))
                self.ui.stat_gui_queue.setText(str(message.gui))
                self.ui.stat_app_detection_queue.setText(str(message.app_detection))

                if self.state == ipc.TrackingState.Running:
                    self.ui.stat_tracking_state.setText('Running' if message.tracking <= 5 else 'Busy')
                    self.ui.stat_processing_state.setText('Running' if message.processing <= 5 else 'Busy')
                    self.ui.stat_hub_state.setText('Running' if message.hub <= 5 else 'Busy')
                    self.ui.stat_app_state.setText('Running' if message.app_detection <= 5 else 'Busy')
                else:
                    for widget in (self.ui.stat_tracking_state, self.ui.stat_processing_state,
                                   self.ui.stat_hub_state, self.ui.stat_app_state):
                        widget.setText('Paused' if self.state == ipc.TrackingState.Paused else 'Stopped')

            case ipc.InvalidConsole():
                self.ui.prefs_console.setEnabled(False)

            case ipc.CloseSplashScreen():
                self.close_splash_screen.emit()

            # Load a legacy profile and switch to it
            case ipc.LoadLegacyProfile():
                self._profile_names.append(message.name)
                self._redraw_profile_combobox()
                self.ui.current_profile.setCurrentIndex(self._profile_names.index(message.name))

            case ipc.ExportStatsSuccessful():
                msg = AutoCloseMessageBox(self)
                msg.setWindowTitle(f'Export Successful')
                msg.setText(f'"{message.source.path}" was successfully saved.')
                msg.setIcon(QtWidgets.QMessageBox.Icon.Information)
                msg.exec_with_timeout('Closing notification', GlobalConfig.export_notification_timeout)

            case ipc.ReloadAppList():
                self._last_app_reload_time = int(time.time() * 10)

    @QtCore.Slot()
    def start_tracking(self) -> None:
        """Start/unpause the tracking."""
        self.cursor_data.position = get_cursor_pos()  # Prevent erroneous line jumps
        self.component.send_data(ipc.StartTracking())
        self.ui.save.setEnabled(True)
        self.ui.thumbnail_refresh.setEnabled(True)
        self.set_profile_modified_text()

    @QtCore.Slot()
    def pause_tracking(self) -> None:
        """Pause/unpause the tracking."""
        self.component.send_data(ipc.PauseTracking())
        self.ui.save.setEnabled(True)
        self.ui.thumbnail_refresh.setEnabled(True)
        self.set_profile_modified_text()

    @QtCore.Slot()
    def stop_tracking(self) -> None:
        """Stop the tracking."""
        self.component.send_data(ipc.StopTracking())

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
    def shut_down(self, force: bool = False) -> None:
        """Trigger a safe shutdown of the application."""
        # If invisible then the close event does not end the QApplication
        if not self.isVisible():
            self.show()

        self._force_close = force
        self.close()

    @QtCore.Slot(QtWidgets.QSystemTrayIcon.ActivationReason)
    def tray_activated(self, reason: QtWidgets.QSystemTrayIcon.ActivationReason) -> None:
        """What to do when the tray icon is activated."""
        match reason:
            case QtWidgets.QSystemTrayIcon.ActivationReason.DoubleClick:
                self.load_from_tray()

            case QtWidgets.QSystemTrayIcon.ActivationReason.Context:
                self.ui.tray_show.setVisible(not self.isVisible())
                self.ui.tray_hide.setVisible(self.isVisible())

                # Determine if the debug menu should be visible
                modifiers = QtGui.QGuiApplication.queryKeyboardModifiers()
                shift_held = modifiers & QtCore.Qt.KeyboardModifier.ShiftModifier
                self.ui.menu_debug.menuAction().setVisible(bool(shift_held))

                # Show the menu
                self.ui.tray_context_menu.exec(QtGui.QCursor.pos())

    def hide_to_tray(self) -> None:
        """Minimise the window to the tray."""
        if self.tray is None or not self.ui.menu_allow_minimise.isChecked():
            self.showMinimized()

        elif self.isVisible():
            self.hide()

    def load_from_tray(self) -> None:
        """Load the window from the tray icon.
        If the window is only minimised to the taskbar, then `show()`
        will be ignored.
        """
        if self.isMinimized():
            self.setWindowState(QtCore.Qt.WindowState.WindowActive)

        if self.isVisible():
            self.raise_()
            self.activateWindow()

        else:
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
            self.request_thumbnail()
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

        elif not self._is_closing and not self._is_changing_state:
            self.timer_activity.stop()
            self.ui.thumbnail.clear_pixmap()
            self.notify(f'{self.windowTitle()} is now running in the background.')

        event.accept()

    def ask_to_save(self) -> bool:
        """Ask the user to save.
        Returns True if the close event should proceed.
        """
        # Pause the tracking
        if self.state != ipc.TrackingState.Stopped:
            self.component.send_data(ipc.PauseTracking())

        msg = AutoCloseMessageBox(self)
        msg.setWindowTitle(f'Closing {self.windowTitle()}')
        msg.setText('Do you want to save?')
        msg.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No
                               | QtWidgets.QMessageBox.StandardButton.Cancel)
        msg.setDefaultButton(QtWidgets.QMessageBox.StandardButton.Yes)
        msg.setEscapeButton(QtWidgets.QMessageBox.StandardButton.Cancel)

        match msg.exec_with_timeout('Saving automatically', GlobalConfig.shutdown_timeout):
            case QtWidgets.QMessageBox.StandardButton.Cancel:
                if self.state != ipc.TrackingState.Stopped:
                    self.component.send_data(ipc.StartTracking())
                return False

            case QtWidgets.QMessageBox.StandardButton.Yes:
                QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.CursorShape.WaitCursor)
                self.setEnabled(False)
                self.component.send_data(ipc.Save())
                self._waiting_on_save = True
        return True

    def _handle_close_event(self) -> bool:
        """Handle saving as part of the close event."""
        is_closing, self._is_closing = self._is_closing, True

        # Close now if no tracking is running
        if self.state == ipc.TrackingState.Stopped:
            return True

        # Allow the user to cancel
        if not self._force_close:

            # Prevent closing again while a save is being attempted
            if is_closing:
                return False

            # Reset flags
            self._waiting_on_save = False
            self._last_save_message = None
            if not self.ask_to_save():
                self._is_closing = False
                return False

        # If the flag is not set, then no save was requested
        if not self._waiting_on_save:
            return True

        # Ignore the event if no save message has been received
        if self._last_save_message is None:
            return False

        # All profiles saved successfully
        if not self._last_save_message.failed:
            return True

        # Ask the user to discard unsaved data
        msg = QtWidgets.QMessageBox()
        msg.setWindowTitle('Save Failed')
        msg.setIcon(QtWidgets.QMessageBox.Icon.Warning)
        msg.setText('Not all profiles were saved.\n'
                    f'  Successful: {", ".join(self._last_save_message.succeeded)}\n'
                    f'  Failed: {", ".join(self._last_save_message.failed)}\n'
                    '\n'
                    'Do you want to continue shutting down?\n'
                    'All unsaved data will be lost.')
        msg.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No)
        msg.setDefaultButton(QtWidgets.QMessageBox.StandardButton.Yes)
        msg.setEscapeButton(QtWidgets.QMessageBox.StandardButton.No)

        # Proceed with shutdown
        if msg.exec() == QtWidgets.QMessageBox.StandardButton.Yes:
            return True

        # Reset flags
        self._waiting_on_save = False
        self._is_closing = False
        self._force_close = False
        return False

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        """Handle when the GUI is closed."""
        if self._handle_close_event():
            event.accept()
        else:
            event.ignore()

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

    @property
    def mouse_tracking_enabled(self) -> bool:
        """Determine if mouse tracking is enabled."""
        return self.ui.track_mouse.isChecked() and self.ui.prefs_track_mouse.isChecked()

    def draw_pixmap_line(self, old_position: tuple[int, int] | None, new_position: tuple[int, int] | None,
                         force_monitor: tuple[int, int] | None = None) -> None:
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
        width = self.ui.thumbnail.width()
        height = self.ui.thumbnail.height()
        custom_width = self.ui.custom_width.isEnabled()
        custom_height = self.ui.custom_height.isEnabled()
        lock_aspect = self.ui.lock_aspect.isChecked()

        # If the aspect is locked, or both width and height are set
        if lock_aspect or (custom_width and custom_height):
            aspect_mode = QtCore.Qt.AspectRatioMode.KeepAspectRatio

        # If the custom width or height is too low
        elif custom_width < width or custom_height < height:
            aspect_mode = QtCore.Qt.AspectRatioMode.KeepAspectRatio

        # Allow the render to fill the widget
        else:
            aspect_mode = QtCore.Qt.AspectRatioMode.IgnoreAspectRatio

        if self.ui.thumbnail.freeze_scale(aspect_mode):
            self.request_thumbnail()

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

        if msg.exec() == QtWidgets.QMessageBox.StandardButton.Yes:
            self._delete_mouse_pressed = True
            self.handle_delete_button_visibility()
            self.component.send_data(ipc.DeleteMouseData(profile))
            self.mark_profiles_unsaved(profile)
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

        if msg.exec() == QtWidgets.QMessageBox.StandardButton.Yes:
            self._delete_keyboard_pressed = True
            self.handle_delete_button_visibility()
            self.component.send_data(ipc.DeleteKeyboardData(profile))
            self.mark_profiles_unsaved(profile)
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

        if msg.exec() == QtWidgets.QMessageBox.StandardButton.Yes:
            self._delete_gamepad_pressed = True
            self.handle_delete_button_visibility()
            self.component.send_data(ipc.DeleteGamepadData(profile))
            self.mark_profiles_unsaved(profile)
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

        if msg.exec() == QtWidgets.QMessageBox.StandardButton.Yes:
            self._delete_network_pressed = True
            self.handle_delete_button_visibility()
            self.component.send_data(ipc.DeleteNetworkData(profile))
            self.mark_profiles_unsaved(profile)
            self._redraw_profile_combobox()
            self.request_profile_data(profile)

    def delete_profile(self) -> None:
        """Delete the selected profile."""
        profile = self.ui.current_profile.currentData()

        msg = QtWidgets.QMessageBox(self)
        msg.setIcon(QtWidgets.QMessageBox.Icon.Critical)
        msg.setWindowTitle('Delete Profile')
        msg.setText(f'Are you sure you want to delete all data for {profile}?\n'
                    'This action cannot be undone.')
        msg.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No)
        msg.setDefaultButton(QtWidgets.QMessageBox.StandardButton.No)
        msg.setEscapeButton(QtWidgets.QMessageBox.StandardButton.No)

        if msg.exec() == QtWidgets.QMessageBox.StandardButton.Yes:
            self.component.send_data(ipc.DeleteProfile(profile))
            self.mark_profiles_saved(profile)
            del self._profile_names[self._profile_names.index(profile)]
            self._unsaved_profiles.discard(profile)

            self._redraw_profile_combobox()
            self.profile_changed(0)

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

    @QtCore.Slot(bool)
    def set_mouse_tracking_enabled(self, value: bool) -> None:
        self.config.track_mouse = value
        self.config.save()
        self.component.send_data(ipc.SetGlobalMouseTracking(value))

    @QtCore.Slot(bool)
    def set_keyboard_tracking_enabled(self, value: bool) -> None:
        self.config.track_keyboard = value
        self.config.save()
        self.component.send_data(ipc.SetGlobalKeyboardTracking(value))

    @QtCore.Slot(bool)
    def set_gamepad_tracking_enabled(self, value: bool) -> None:
        self.config.track_gamepad = value
        self.config.save()
        self.component.send_data(ipc.SetGlobalGamepadTracking(value))

    @QtCore.Slot(bool)
    def set_network_tracking_enabled(self, value: bool) -> None:
        self.config.track_network = value
        self.config.save()
        self.component.send_data(ipc.SetGlobalNetworkTracking(value))

    def mark_profiles_saved(self, *profile_names: str) -> None:
        """Mark profiles as saved."""
        self._unsaved_profiles -= set(profile_names)
        self.set_profile_modified_text()

    def mark_profiles_unsaved(self, *profile_names: str) -> None:
        """Mark profiles as unsaved."""
        self._unsaved_profiles |= set(profile_names)
        self.set_profile_modified_text()

    def set_profile_modified_text(self) -> None:
        """Set the text if the profile has been modified."""
        if self.ui.current_profile.currentData() in self._unsaved_profiles:
            self.ui.profile_modified.setText('Yes')
            self.ui.profile_save.setEnabled(self.state != ipc.TrackingState.Stopped)
        else:
            self.ui.profile_modified.setText('No')
            self.ui.profile_save.setEnabled(False)

    def handle_delete_button_visibility(self, _: Any = None) -> None:
        """Toggle the delete button visibility.

        They are only enabled when tracking is disabled, and when
        processing is not waiting to delete. Deleting a profile is only
        allowed once all tracking is disabled as a safety measure.
        """
        delete_mouse = not self.ui.track_mouse.isChecked() and not self._delete_mouse_pressed
        delete_keyboard = not self.ui.track_keyboard.isChecked() and not self._delete_keyboard_pressed
        delete_gamepad = not self.ui.track_gamepad.isChecked() and not self._delete_gamepad_pressed
        delete_network = not self.ui.track_network.isChecked() and not self._delete_network_pressed

        self.ui.delete_mouse.setEnabled(delete_mouse)
        self.ui.delete_keyboard.setEnabled(delete_keyboard)
        self.ui.delete_gamepad.setEnabled(delete_gamepad)
        self.ui.delete_network.setEnabled(delete_network)
        self.ui.delete_profile.setEnabled(delete_mouse and delete_keyboard and delete_gamepad and delete_network)

    @QtCore.Slot(bool)
    def set_autostart(self, value: bool) -> None:
        """Set if the application runs on startup.
        This only works on the built executable as it adds it to the
        registry. If the executable is moved then it will need to be
        re-added.
        """
        if not self.ui.prefs_autostart.isEnabled():
            return

        if value:
            args = sys.argv
            if args and os.path.normpath(args[0]) == os.path.normpath(SYS_EXECUTABLE):
                args = args[1:]
            set_autostart(*args, '--autostart')

        else:
            remove_autostart()

        self.notify(f'{self.windowTitle()} will {"now" if value else "no longer"} launch when Windows starts.')

    @QtCore.Slot(bool)
    def set_minimise_on_start(self, value: bool) -> None:
        """Set if the app should minimise on startup.
        This saves a config value which is read the next time it loads.
        """
        self.config.minimise_on_start = value
        self.config.save()

    @QtCore.Slot(bool)
    def set_always_on_top(self, value: bool) -> None:
        """Set if the window is always on top."""
        self._is_changing_state = True
        flags = self.windowFlags()
        if value:
            flags |= QtCore.Qt.WindowType.WindowStaysOnTopHint.value
        else:
            flags &= ~QtCore.Qt.WindowType.WindowStaysOnTopHint.value
        self.setWindowFlags(flags)
        self.show()
        self._is_changing_state = False

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

    @QtCore.Slot(bool)
    def toggle_advanced_options(self, show_advanced: bool) -> None:
        """Set the visibility of render option widgets."""
        is_click = self.render_type in (ipc.RenderType.SingleClick, ipc.RenderType.DoubleClick, ipc.RenderType.HeldClick)
        is_thumbstick = self.render_type in (ipc.RenderType.Thumbstick_Time, ipc.RenderType.Thumbstick_Speed, ipc.RenderType.Thumbstick_Heatmap)
        is_keyboard = self.render_type == ipc.RenderType.Keyboard

        self.ui.show_left_clicks.setVisible(show_advanced and (is_click or is_thumbstick))
        self.ui.show_middle_clicks.setVisible(show_advanced and is_click)
        self.ui.show_right_clicks.setVisible(show_advanced and (is_click or is_thumbstick))

        self.ui.show_count.setVisible(show_advanced and is_keyboard)
        self.ui.show_time.setVisible(show_advanced and is_keyboard)

        self.ui.contrast.setVisible(show_advanced and not is_keyboard)
        self._buddies[self.ui.contrast].setVisible(show_advanced and not is_keyboard)
        self.ui.sampling.setVisible(show_advanced)
        self._buddies[self.ui.sampling].setVisible(show_advanced)
        self.ui.thumbnail_sampling.setVisible(show_advanced)
        self._buddies[self.ui.thumbnail_sampling].setVisible(show_advanced)
        self.ui.padding.setVisible(show_advanced and not is_keyboard)
        self._buddies[self.ui.padding].setVisible(show_advanced and not is_keyboard)
        self.ui.clipping.setVisible(show_advanced and not is_keyboard)
        self._buddies[self.ui.clipping].setVisible(show_advanced and not is_keyboard)
        self.ui.blur.setVisible(show_advanced and not is_keyboard)
        self._buddies[self.ui.blur].setVisible(show_advanced and not is_keyboard)
        self.ui.linear.setVisible(show_advanced and not is_keyboard)
        self.ui.interpolation_order.setVisible(show_advanced and not is_keyboard)
        self._buddies[self.ui.interpolation_order].setVisible(show_advanced and not is_keyboard)

        self.ui.resolution_group.setVisible(show_advanced and not is_keyboard)

    def notify(self, message: str) -> None:
        """Show a notification.
        If the tray messages are not available, a popup will be shown.
        """
        if self.tray is None or not self.tray.supportsMessages():
            if self.isVisible():
                msg = QtWidgets.QMessageBox(self)
                msg.setWindowTitle(self.windowTitle())
                msg.setIcon(QtWidgets.QMessageBox.Icon.Information)
                msg.setText(message)
                msg.exec()
        else:
            self.tray.showMessage(self.windowTitle(), message, self.tray.icon(), 2000)

    @QtCore.Slot()
    def import_legacy_profile(self) -> None:
        """Prompt the user to import a legacy profile.
        A check is done to avoid name clashes.
        """
         # Get the default legacy location if available
        documents_path = _get_docs_folder()
        default_dir = documents_path / 'Mouse Tracks' / 'Data'
        if not default_dir.exists():
            default_dir = documents_path

        # Select the profile
        path, filter = QtWidgets.QFileDialog.getOpenFileName(self, 'Select Legacy Profile',
                                                             str(default_dir),
                                                             'MouseTracks Profile (*.mtk)')
        if not path:
            return

        # Ask for the profile name
        filename = QtCore.QFileInfo(path).baseName()
        while True:
            name, accept = QtWidgets.QInputDialog.getText(self, 'Profile Name', 'Enter the name of the profile:',
                                                          QtWidgets.QLineEdit.EchoMode.Normal, filename)
            if not accept:
                return

            # Check if the profile already exists
            if not PROFILE_DIR.exists():
                break
            name = name.strip() or filename
            if os.path.basename(get_filename(name)) not in os.listdir(PROFILE_DIR):
                break

            # Show a warning
            msg = QtWidgets.QMessageBox()
            msg.setIcon(QtWidgets.QMessageBox.Icon.Critical)
            msg.setWindowTitle('Error')
            msg.setText('This profile already exists.\n\n'
                        'To avoid accidental overwrites, please delete the existing profile or choose a new name.')
            msg.exec()

        # Send the request
        self.component.send_data(ipc.LoadLegacyProfile(name.strip() or filename, path))

    @QtCore.Slot()
    def export_mouse_stats(self) -> None:
        """Export the mouse statistics."""
        dialog = QtWidgets.QFileDialog()
        dialog.setAcceptMode(QtWidgets.QFileDialog.AcceptMode.AcceptSave)
        dialog.setNameFilters(['CSV Files (*.csv)"'])
        dialog.setDefaultSuffix('csv')

        profile = self.ui.current_profile.currentData()
        profile_safe = re.sub(r'[^\w_.)( -]', '', profile)
        export_dir = _get_docs_folder() / f'[{format_ticks(self.elapsed_time)}] {profile_safe} - Mouse Stats.csv'

        file_path, accept = dialog.getSaveFileName(self, 'Save Mouse Stats', str(export_dir), 'CSV Files (*.csv)')
        if accept:
            self.component.send_data(ipc.ExportMouseStats(self.ui.current_profile.currentData(), file_path))

    @QtCore.Slot()
    def export_keyboard_stats(self) -> None:
        """Export the keyboard statistics."""
        dialog = QtWidgets.QFileDialog()
        dialog.setAcceptMode(QtWidgets.QFileDialog.AcceptMode.AcceptSave)
        dialog.setNameFilters(['CSV Files (*.csv)"'])
        dialog.setDefaultSuffix('csv')

        profile = self.ui.current_profile.currentData()
        profile_safe = re.sub(r'[^\w_.)( -]', '', profile)
        export_dir = _get_docs_folder() / f'[{format_ticks(self.elapsed_time)}] {profile_safe} - Keyboard Stats.csv'

        file_path, accept = dialog.getSaveFileName(self, 'Save Keyboard Stats', str(export_dir), 'CSV Files (*.csv)')
        if accept:
            self.component.send_data(ipc.ExportKeyboardStats(self.ui.current_profile.currentData(), file_path))

    @QtCore.Slot()
    def export_gamepad_stats(self) -> None:
        """Export the gamepad statistics."""
        dialog = QtWidgets.QFileDialog()
        dialog.setAcceptMode(QtWidgets.QFileDialog.AcceptMode.AcceptSave)
        dialog.setNameFilters(['CSV Files (*.csv)"'])
        dialog.setDefaultSuffix('csv')

        profile = self.ui.current_profile.currentData()
        profile_safe = re.sub(r'[^\w_.)( -]', '', profile)
        export_dir = _get_docs_folder() / f'[{format_ticks(self.elapsed_time)}] {profile_safe} - Gamepad Stats.csv'

        file_path, accept = dialog.getSaveFileName(self, 'Save Gamepad Stats', str(export_dir), 'CSV Files (*.csv)')
        if accept:
            self.component.send_data(ipc.ExportGamepadStats(self.ui.current_profile.currentData(), file_path))

    @QtCore.Slot()
    def export_network_stats(self) -> None:
        """Export the network statistics."""
        dialog = QtWidgets.QFileDialog()
        dialog.setAcceptMode(QtWidgets.QFileDialog.AcceptMode.AcceptSave)
        dialog.setNameFilters(['CSV Files (*.csv)"'])
        dialog.setDefaultSuffix('csv')

        profile = self.ui.current_profile.currentData()
        profile_safe = re.sub(r'[^\w_.)( -]', '', profile)
        export_dir = _get_docs_folder() / f'[{format_ticks(self.elapsed_time)}] {profile_safe} - Network Stats.csv'

        file_path, accept = dialog.getSaveFileName(self, 'Save Network Stats', str(export_dir), 'CSV Files (*.csv)')
        if accept:
            self.component.send_data(ipc.ExportNetworkStats(self.ui.current_profile.currentData(), file_path))

    @QtCore.Slot()
    def export_daily_stats(self) -> None:
        """Export the daily statistics."""
        dialog = QtWidgets.QFileDialog()
        dialog.setAcceptMode(QtWidgets.QFileDialog.AcceptMode.AcceptSave)
        dialog.setNameFilters(['CSV Files (*.csv)"'])
        dialog.setDefaultSuffix('csv')

        profile = self.ui.current_profile.currentData()
        profile_safe = re.sub(r'[^\w_.)( -]', '', profile)
        export_dir = _get_docs_folder() / f'[{format_ticks(self.elapsed_time)}] {profile_safe} - Daily Stats.csv'

        file_path, accept = dialog.getSaveFileName(self, 'Save Daily Stats', str(export_dir), 'CSV Files (*.csv)')
        if accept:
            self.component.send_data(ipc.ExportDailyStats(self.ui.current_profile.currentData(), file_path))

