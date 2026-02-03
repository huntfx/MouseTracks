from __future__ import annotations

import os
import math
import random
import re
import sys
import time
import webbrowser
import zipfile
from contextlib import suppress
from dataclasses import dataclass, field
from pathlib import Path
from typing import cast, Any, Generic, Iterable, Iterator, TypeVar, TYPE_CHECKING

import numpy as np
from PIL import Image
from PySide6 import QtCore, QtWidgets, QtGui

from .about import AboutWindow
from .applist import AppListWindow
from .ui import layout
from .utils import format_distance, format_ticks, format_bytes, format_network_speed, ICON_PATH
from .widgets import Pixel, AutoCloseMessageBox
from ..components import ipc
from ..constants import SYS_EXECUTABLE
from ..config import should_minimise_on_start, CLI, GlobalConfig
from ..constants import COMPRESSION_FACTOR, COMPRESSION_THRESHOLD, DEFAULT_PROFILE_NAME, RADIAL_ARRAY_SIZE
from ..constants import UPDATES_PER_SECOND, IS_EXE, TRACKING_DISABLE
from ..enums import BlendMode, Channel
from ..file import PROFILE_DIR, get_profile_names, get_filename, sanitise_profile_name, TrackingProfile
from ..legacy import colours
from ..update import is_latest_version
from ..types import RectList
from ..utils import keycodes
from ..utils.input import get_cursor_pos
from ..utils.math import calculate_line, calculate_distance
from ..utils.monitor import MonitorData
from ..utils.system import get_autostart, set_autostart, remove_autostart

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
    rects: RectList = field(default_factory=RectList)
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
            case (ipc.RenderType.MouseMovement | ipc.RenderType.ThumbstickMovement):
                return self.movement
            case ipc.RenderType.MouseSpeed | ipc.RenderType.ThumbstickSpeed:
                return self.speed
            case (ipc.RenderType.SingleClick | ipc.RenderType.DoubleClick | ipc.RenderType.HeldClick
                  | ipc.RenderType.ThumbstickPosition | ipc.RenderType.MousePosition):
                return self.heatmap
            case ipc.RenderType.KeyboardHeatmap:
                return self.keyboard
            case _:
                raise NotImplementedError(f'Unsupported render type: {render_type}')

    def set(self, render_type: ipc.RenderType, value: T) -> None:
        """Set the value for a render type."""
        match render_type:
            case (ipc.RenderType.MouseMovement | ipc.RenderType.ThumbstickMovement):
                self.movement = value
            case ipc.RenderType.MouseSpeed | ipc.RenderType.ThumbstickSpeed:
                self.speed = value
            case (ipc.RenderType.SingleClick | ipc.RenderType.DoubleClick | ipc.RenderType.HeldClick
                  | ipc.RenderType.ThumbstickPosition | ipc.RenderType.MousePosition):
                self.heatmap = value
            case ipc.RenderType.KeyboardHeatmap:
                self.keyboard = value
            case _:
                raise NotImplementedError(f'Unsupported render type: {render_type}')


@dataclass
class LayerOption:
    render_type: ipc.RenderType
    blend_mode: BlendMode = BlendMode.Normal
    channels: Channel = Channel.RGBA
    opacity: int = 100
    render_colour: RenderOption = field(default_factory=lambda: RenderOption('Ice', 'Ice', 'Jet', 'Aqua'))
    contrast: RenderOption = field(default_factory=lambda: RenderOption(1.0, 1.0, 1.0, 1.0))
    padding: RenderOption = field(default_factory=lambda: RenderOption(0, 0, 0, 0))
    clipping: RenderOption = field(default_factory=lambda: RenderOption(0.0, 0.0, 0.001, 0.0))
    blur: RenderOption = field(default_factory=lambda: RenderOption(0.0, 0.0, 0.0125, 0.0))
    linear: RenderOption = field(default_factory=lambda: RenderOption(False, True, True, False))
    invert: RenderOption = field(default_factory=lambda: RenderOption(False, False, False, False))
    show_left_clicks: bool = True
    show_middle_clicks: bool = True
    show_right_clicks: bool = True


@dataclass
class NetworkSpeedStats:
    """Store data for the "Current Upload/Download" stats."""

    _message: ipc.DataTransfer | None = None
    _last_changed: float = field(default_factory=time.time)
    _counter: int = 0
    _EMPTY = ipc.DataTransfer('', 0, 0)

    def set(self, message: ipc.DataTransfer) -> None:
        """Set the current `DataTransfer` message."""
        self._message = message
        self._last_changed = time.time()

    def get(self) -> ipc.DataTransfer:
        """Get the current `DataTransfer` message."""
        # Check if the data is too out of date (with extra leeway)
        if time.time() > self._last_changed + 1.05:
            return self._EMPTY

        # Get the saved message
        if self._message is not None:
            return self._message
        return self._EMPTY

    @property
    def bytes_recv(self) -> int:
        """Get the number of bytes received."""
        return self.get().bytes_recv

    @property
    def bytes_sent(self) -> int:
        """Get the number of bytes sent."""
        return self.get().bytes_sent


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
        self._pixel_colour_cache: dict[str, tuple[QtGui.QColor, QtGui.QColor] | None] = {}
        self._is_setting_click_state = False
        self._force_close = False
        self._waiting_on_save = False
        self._last_save_message: ipc.SaveComplete | None
        self._thumbnail_redraw_required = False
        self._resolution_options: dict[tuple[int, int], bool] = {}
        self._is_updating_layer_options = False
        self._window_ready = False
        self._startup_notify_queue: list[str] = []
        self._network_speed = NetworkSpeedStats()
        self.state = ipc.TrackingState.Paused

        # Setup UI
        self.ui = layout.Ui_MainWindow()
        self.ui.setupUi(self)

        # Set initial widget states
        self.ui.statusbar.setVisible(False)
        self.ui.output_logs.setVisible(False)
        self.ui.record_history.setVisible(False)
        self.ui.tray_context_menu.menuAction().setVisible(False)
        try:
            self.ui.prefs_autostart.setChecked(get_autostart() is not None)
        except NotImplementedError:
            self.ui.prefs_autostart.setEnabled(False)
        self.ui.prefs_automin.setChecked(self.config.minimise_on_start)
        self.ui.prefs_track_mouse.setChecked(self.config.track_mouse)
        self.ui.prefs_track_keyboard.setChecked(self.config.track_keyboard)
        self.ui.prefs_track_gamepad.setChecked(self.config.track_gamepad)
        self.ui.prefs_track_network.setChecked(self.config.track_network)
        self.ui.contrast.setMaximum(float('inf'))
        self.update_focused_application('', '', False)

        self.ui.layer_presets.installEventFilter(self)

        # Hide social links for now
        self.ui.link_reddit.setVisible(False)
        self.ui.link_facebook.setVisible(False)

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
            self.tray.setContextMenu(self.ui.tray_context_menu)
            self.tray.activated.connect(self.tray_activated)
        else:
            self.tray = None
            self.ui.menu_allow_minimise.setChecked(False)
            self.ui.menu_allow_minimise.setEnabled(False)

        self.current_profile = Profile(DEFAULT_PROFILE_NAME)
        #self.update_profile_combobox(DEFAULT_PROFILE_NAME)

        # self.ui.map_type = QtWidgets.QComboBox()
        self.ui.map_type.addItem('[Mouse] Movement', ipc.RenderType.MouseMovement)
        self.ui.map_type.addItem('[Mouse] Speed', ipc.RenderType.MouseSpeed)
        self.ui.map_type.addItem('[Mouse] Position', ipc.RenderType.MousePosition)
        self.ui.map_type.addItem('[Mouse] Clicks', ipc.RenderType.SingleClick)
        self.ui.map_type.addItem('[Mouse] Double Clicks', ipc.RenderType.DoubleClick)
        self.ui.map_type.addItem('[Mouse] Held Clicks', ipc.RenderType.HeldClick)
        self.ui.map_type.addItem('[Keyboard] Key Presses', ipc.RenderType.KeyboardHeatmap)
        self.ui.map_type.addItem('[Thumbsticks] Movement', ipc.RenderType.ThumbstickMovement)
        self.ui.map_type.addItem('[Thumbsticks] Speed', ipc.RenderType.ThumbstickSpeed)
        self.ui.map_type.addItem('[Thumbsticks] Position', ipc.RenderType.ThumbstickPosition)

        self.cursor_data = MapData(get_cursor_pos())
        self.thumbstick_l_data = MapData((0, 0))
        self.thumbstick_r_data = MapData((0, 0))
        self._sampling = 4
        self._sampling_preview = 0

        self._layers: dict[int, LayerOption] = {}
        self._layer_counter = 0
        self._selected_layer = 0
        self.ui.layer_list.clear()
        for enum in BlendMode:
            self.ui.layer_blending.addItem(enum.name, enum)
        background_layer = self.add_render_layer()
        background_layer.setCheckState(QtCore.Qt.CheckState.Checked)
        background_layer.setSelected(True)

        self.mouse_click_count = self.mouse_held_count = self.mouse_scroll_count = 0
        self.button_press_count = self.key_press_count = 0
        self.elapsed_time = self.active_time = self.inactive_time = 0
        self.monitor_data = MonitorData()
        self.render_type = ipc.RenderType.MouseMovement
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
        self._timer_tip = QtCore.QTimer(self)

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
        self.ui.invert.toggled.connect(self.invert_changed)
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
        self.ui.debug_pause_app.triggered.connect(self.set_app_detection_disabled)
        self.ui.debug_pause_monitor.triggered.connect(self.set_monitor_check_disabled)
        self.ui.full_screen.triggered.connect(self.toggle_full_screen)
        self.ui.file_import.triggered.connect(self.import_profile)
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
        self.ui.layer_list.currentItemChanged.connect(self.selected_layer_changed)
        self.ui.layer_list.itemChanged.connect(self.selected_layer_toggled)
        self.ui.layer_list.model().rowsMoved.connect(self.selected_layer_moved)
        self.ui.layer_blending.currentIndexChanged.connect(self.layer_blend_mode_changed)
        self.ui.layer_opacity.valueChanged.connect(self.layer_opacity_changed)
        self.ui.layer_r.toggled.connect(self.layer_channel_changed)
        self.ui.layer_g.toggled.connect(self.layer_channel_changed)
        self.ui.layer_b.toggled.connect(self.layer_channel_changed)
        self.ui.layer_a.toggled.connect(self.layer_channel_changed)
        self.ui.layer_add.clicked.connect(self.add_render_layer)
        self.ui.layer_remove.clicked.connect(self.delete_render_layer)
        self.ui.layer_up.clicked.connect(self.move_layer_up)
        self.ui.layer_down.clicked.connect(self.move_layer_down)
        self.ui.layer_presets.currentIndexChanged.connect(self.layer_preset_chosen)
        self.ui.tray_context_menu.aboutToShow.connect(self.update_tray_menu)
        self.timer_activity.timeout.connect(self.update_activity_preview)
        self.timer_activity.timeout.connect(self.update_time_since_save)
        self.timer_activity.timeout.connect(self.update_time_since_thumbnail)
        self.timer_activity.timeout.connect(self.update_time_since_applist_reload)
        self.timer_activity.timeout.connect(self.update_queue_size)
        self.timer_activity.timeout.connect(self.update_current_network_stats)
        self._timer_thumbnail_update.timeout.connect(self._request_thumbnail)
        self._timer_resize.timeout.connect(self.update_thumbnail_size)
        self._timer_rendering.timeout.connect(self.ui.thumbnail.show_rendering_text)
        self._timer_tip.timeout.connect(self.set_random_tip_text)

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
        self.selected_layer_changed(background_layer, None)
        if not self.ui.layer_blending.currentIndex():
            self.layer_blend_mode_changed(0)

        self.component.send_data(ipc.RequestPID(ipc.Target.Hub))
        self.component.send_data(ipc.RequestPID(ipc.Target.Tracking))
        self.component.send_data(ipc.RequestPID(ipc.Target.Processing))
        self.component.send_data(ipc.RequestPID(ipc.Target.GUI))
        self.component.send_data(ipc.RequestPID(ipc.Target.AppDetection))

        self.ui.layer_presets.addItem('Reset')
        self.ui.layer_presets.addItem('Heatmap Overlay')
        self.ui.layer_presets.addItem('Heatmap Tracks')
        self.ui.layer_presets.addItem('Alpha Multiply')
        self.ui.layer_presets.addItem('Urban Grass')
        self.ui.layer_presets.addItem('Eraser')
        self.ui.layer_presets.addItem('Plasma')
        self.ui.layer_presets.addItem('RGB Clicks')

    def eventFilter(self, obj: QtCore.QObject, event: QtCore.QEvent) -> bool:
        # Ignore scroll events on the layer presets combobox
        if obj is self.ui.layer_presets and event.type() == QtCore.QEvent.Type.Wheel:
            event.ignore()
            return True
        return super().eventFilter(obj, event)

    def on_app_ready(self) -> None:
        """Run code when the application is ready to start."""
        self._window_ready = True
        if not should_minimise_on_start():
            self.show()
        if self.tray is not None:
            self.tray.show()

        while self._startup_notify_queue:
            self.notify(self._startup_notify_queue.pop(0))

    def set_tip_timer_state(self, enabled: bool) -> None:
        """Set the state of the tip update timer.
        The text update function is triggered every 10 minutes.
        """
        if enabled:
            self.set_random_tip_text()
            self._timer_tip.start(600000)
        else:
            self._timer_tip.stop()

    @QtCore.Slot()
    def set_random_tip_text(self) -> None:
        """Text a random tip."""
        tips = ['tip_tracking', 'tip_tooltip']
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
                self._pixel_colour_cache[colour_map] = QtGui.QColor(*generated_map[-1]), QtGui.QColor(*generated_map[0])

        colour = self._pixel_colour_cache[colour_map]
        if colour is None:
            return QtGui.QColor(QtCore.Qt.GlobalColor.transparent)
        return colour[self.invert]

    @property
    def render_type(self) -> ipc.RenderType:
        """Get the render type."""
        return self.selected_layer.render_type

    @render_type.setter
    def render_type(self, render_type: ipc.RenderType) -> None:
        """Set the render type.
        This populates the available colour maps.
        """
        self.selected_layer.render_type = render_type

        # Add items to render colour input
        self.pause_colour_change = True

        self.ui.colour_option.clear()

        colour_maps = colours.get_map_matches(
            tracks=render_type in (ipc.RenderType.MouseMovement, ipc.RenderType.MouseSpeed,
                                   ipc.RenderType.ThumbstickMovement, ipc.RenderType.ThumbstickSpeed),
            clicks=render_type in (ipc.RenderType.SingleClick, ipc.RenderType.DoubleClick, ipc.RenderType.HeldClick,
                                   ipc.RenderType.ThumbstickPosition, ipc.RenderType.MousePosition),
            keyboard=render_type == ipc.RenderType.KeyboardHeatmap,
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
        self.ui.invert.setChecked(self.invert)
        self.ui.show_left_clicks.setChecked(self.show_left_clicks)
        self.ui.show_middle_clicks.setChecked(self.show_middle_clicks)
        self.ui.show_right_clicks.setChecked(self.show_right_clicks)
        self.toggle_advanced_options(self.ui.show_advanced.isChecked())

        self.pause_colour_change = False

    @property
    def render_colour(self) -> str:
        """Get the render colour for the current render type."""
        return self.selected_layer.render_colour.get(self.render_type)

    @render_colour.setter
    def render_colour(self, colour: str) -> None:
        """Set the render colour for the current render type.
        This will update the current pixel colour too.
        """
        self.selected_layer.render_colour.set(self.render_type, colour)

    @property
    def contrast(self) -> float:
        """Get the contrast for the current render type."""
        return self.selected_layer.contrast.get(self.render_type)

    @contrast.setter
    def contrast(self, value: float) -> None:
        """Set a new constrast value for the current render type."""
        self.selected_layer.contrast.set(self.render_type, value)

    @property
    def sampling(self) -> int:
        """Get the sampling for the current render type."""
        return self._sampling

    @sampling.setter
    def sampling(self, value: int) -> None:
        """Set a new sampling value for the current render type."""
        self._sampling = value

    @property
    def sampling_preview(self) -> int:
        """Get the thumbnail sampling for the current render type."""
        return self._sampling_preview

    @sampling_preview.setter
    def sampling_preview(self, value: int) -> None:
        """Set a new thumbnail sampling value for the current render type."""
        self._sampling_preview = value

    @property
    def padding(self) -> int:
        """Get the padding for the current render type."""
        return self.selected_layer.padding.get(self.render_type)

    @padding.setter
    def padding(self, value: int) -> None:
        """Set a new padding value for the current render type."""
        self.selected_layer.padding.set(self.render_type, value)

    @property
    def clipping(self) -> float:
        """Get the clipping for the current render type."""
        return self.selected_layer.clipping.get(self.render_type)

    @clipping.setter
    def clipping(self, value: float) -> None:
        """Set a new clipping value for the current render type."""
        self.selected_layer.clipping.set(self.render_type, value)

    @property
    def blur(self) -> float:
        """Get the blur for the current render type."""
        return self.selected_layer.blur.get(self.render_type)

    @blur.setter
    def blur(self, value: float) -> None:
        """Set a new blur value for the current render type."""
        self.selected_layer.blur.set(self.render_type, value)

    @property
    def linear(self) -> bool:
        """Get if linear mapping is enabled for the current render type."""
        return self.selected_layer.linear.get(self.render_type)

    @linear.setter
    def linear(self, value: bool) -> None:
        """Set if linear mapping is enabled for the current render type."""
        self.selected_layer.linear.set(self.render_type, value)

    @property
    def invert(self) -> bool:
        """Get if inverting colours for the current render type."""
        return self.selected_layer.invert.get(self.render_type)

    @invert.setter
    def invert(self, value: bool) -> None:
        """Set if inverting colours for the current render type."""
        self.selected_layer.invert.set(self.render_type, value)

    @property
    def show_left_clicks(self) -> bool:
        """Get if left clicks should be shown for the current render type."""
        return self.selected_layer.show_left_clicks

    @show_left_clicks.setter
    def show_left_clicks(self, value: bool) -> None:
        """Set if left clicks should be shown for the current render type."""
        self.selected_layer.show_left_clicks = value

    @property
    def show_middle_clicks(self) -> bool:
        """Get if middle clicks should be shown for the current render type."""
        return self.selected_layer.show_middle_clicks

    @show_middle_clicks.setter
    def show_middle_clicks(self, value: bool) -> None:
        """Set if middle clicks should be shown for the current render type."""
        self.selected_layer.show_middle_clicks = value

    @property
    def show_right_clicks(self) -> bool:
        """Get if right clicks should be shown for the current render type."""
        return self.selected_layer.show_right_clicks

    @show_right_clicks.setter
    def show_right_clicks(self, value: bool) -> None:
        """Set if right clicks should be shown for the current render type."""
        self.selected_layer.show_right_clicks = value

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
        layout = self.ui.profile_resolutions
        while layout.count():
            item = layout.takeAt(0)
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
        self._save_resolution_options()

    @QtCore.Slot(bool)
    def resolution_toggled(self, value: bool) -> None:
        """Toggle rendering of a particular resolution in a profile."""
        checkbox = cast(QtWidgets.QCheckBox, self.sender())
        sanitised_profile_name, profile_name = self._get_profile_data()
        if sanitised_profile_name is None or profile_name is None:
            return
        width, height = map(int, checkbox.text().split('x'))
        self.component.send_data(ipc.ToggleProfileResolution(sanitised_profile_name, (width, height), value))
        self.mark_profiles_unsaved(profile_name)
        self.request_thumbnail()
        self._save_resolution_options()

    def _save_resolution_options(self) -> None:
        """Save the currently chosen resolution options."""
        self._resolution_options.clear()
        for item in map(self.ui.profile_resolutions.itemAt, range(self.ui.profile_resolutions.count())):
            if isinstance(checkbox := item.widget(), QtWidgets.QCheckBox):
                width, height = map(int, checkbox.text().split('x'))
                self._resolution_options[(width, height)] = checkbox.isChecked()

    @QtCore.Slot()
    def multi_monitor_change(self) -> None:
        """Change the multiple monitor option."""
        if not self.ui.opts_monitor.isChecked():
            return
        sanitised_profile_name, profile_name = self._get_profile_data()
        if sanitised_profile_name is None:
            return
        self.component.send_data(ipc.ToggleProfileMultiMonitor(sanitised_profile_name, self.ui.multi_monitor.isChecked()))

    @QtCore.Slot(bool)
    def multi_monitor_override_toggle(self, checked: bool) -> None:
        """Enable or disable the multi monitor override."""
        if not self.ui.opts_monitor.isEnabled():
            return
        sanitised_profile_name, profile_name = self._get_profile_data()
        if sanitised_profile_name is None:
            return
        self.component.send_data(ipc.ToggleProfileMultiMonitor(sanitised_profile_name, self.ui.multi_monitor.isChecked() if checked else None))

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

    @QtCore.Slot()
    def update_queue_size(self) -> None:
        """Request an update of the queue size."""
        self.component.send_data(ipc.RequestQueueSize())

    @QtCore.Slot()
    def update_current_network_stats(self) -> None:
        """Update the data transfer statistics once per second.
        This relies on the data
        """
        self.ui.stat_download_current.setText(format_network_speed(self._network_speed.bytes_recv))
        self.ui.stat_upload_current.setText(format_network_speed(self._network_speed.bytes_sent))

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
        sanitised = sanitise_profile_name(profile.name)
        if sanitised in self._profile_names:
            del self._profile_names[sanitised]
        self._profile_names = {sanitised: profile.name} | self._profile_names
        self.mark_profiles_unsaved(profile.name)
        self._redraw_profile_combobox()

    def _redraw_profile_combobox(self) -> None:
        """Redraw the profile combobox.
        Any "modified" profiles will have an asterix in front.
        """
        # Pause the signals
        self._redrawing_profiles = True

        # Grab the currently selected profile
        current_profile = self.ui.current_profile.currentData()

        # Add the profiles
        self.ui.current_profile.clear()
        for sanitised_profile_name, profile_name in self._profile_names.items():
            if sanitised_profile_name in self._unsaved_profiles:
                self.ui.current_profile.addItem(f'*{profile_name}', sanitised_profile_name)
            else:
                self.ui.current_profile.addItem(profile_name, sanitised_profile_name)

        # Change back to the previously selected profile
        if self.ui.auto_switch_profile.isChecked():
            self.ui.current_profile.setCurrentIndex(0)
        else:
            idx = self.ui.current_profile.findData(current_profile)
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

        sanitised_profile_name, profile_name = self._get_profile_data()
        if sanitised_profile_name is not None:
            self.component.send_data(ipc.Save(sanitised_profile_name))

    @QtCore.Slot(QtCore.Qt.CheckState)
    def toggle_autosave(self, state: QtCore.Qt.CheckState) -> None:
        """Enable or disable autosaving."""
        self.component.send_data(ipc.Autosave(state == QtCore.Qt.CheckState.Checked.value))

    @QtCore.Slot(int)
    def profile_changed(self, idx: int) -> None:
        """Change the profile and trigger a redraw."""
        sanitised_profile_name, profile_name = self._get_profile_data(idx)

        if sanitised_profile_name is not None and not self._redrawing_profiles:
            self.request_profile_data(sanitised_profile_name)
            if idx:
                self.ui.auto_switch_profile.setChecked(False)
            self.set_profile_modified_text()

    def request_profile_data(self, sanitised_profile_name: str) -> None:
        """Request loading profile data."""
        self.component.send_data(ipc.ProfileDataRequest(sanitised_profile_name,
                                                        self._profile_names[sanitised_profile_name]))

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

    def _get_profile_data(self, idx: int | None = None) -> tuple[str, str] | tuple[None, None]:
        """Get the selected profile name from the combobox."""
        if idx is None:
            sanitised_profile_name = self.ui.current_profile.currentData()
        else:
            sanitised_profile_name = self.ui.current_profile.itemData(idx)
        if sanitised_profile_name is not None:
            return sanitised_profile_name, self._profile_names[sanitised_profile_name]
        return None, None

    @QtCore.Slot(int)
    def render_type_changed(self, idx: int) -> None:
        """Change the render type and trigger a redraw."""
        self.render_type = self.ui.map_type.itemData(idx)
        if not self._is_updating_layer_options:
            self.request_thumbnail()
            self.update_layer_item_name()

    @QtCore.Slot(bool)
    def show_clicks_changed(self, enabled: bool) -> None:
        """Update the render when the click visibility options change.

        Using a shift click is a quick way to check/uncheck all options.
        If shift clicking on a checked option, all other options will be
        unchecked. If shift clicking on an unchecked option, then all
        options will be checked.
        """
        if self._is_setting_click_state or self.pause_colour_change:
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

        self.show_left_clicks = self.ui.show_left_clicks.isChecked()
        self.show_middle_clicks = self.ui.show_middle_clicks.isChecked()
        self.show_right_clicks = self.ui.show_right_clicks.isChecked()

        self.request_thumbnail()
        self.update_layer_item_name()
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

    @QtCore.Slot(bool)
    def invert_changed(self, value: bool) -> None:
        """Update the render when the invert option is changed."""
        if self.pause_colour_change:
            return
        self.invert = value
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
        monitors = self.monitor_data.physical
        if self.current_profile.rects:
            monitors = self.current_profile.rects

        single_monitor = self.ui.single_monitor.isChecked() if self.ui.opts_monitor.isChecked() else bool(CLI.single_monitor)
        return monitors.calculate_offset(pixel, combined=single_monitor)

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

        # Prevent too many requests from queuing up
        # This ensures there's at most 2
        if self.pause_redraw:
            self._thumbnail_redraw_required = True
            return True

        # Flag if drawing to prevent building up duplicate commands
        self.pause_redraw += 1

        width = self.ui.thumbnail.width()
        height = self.ui.thumbnail.height()
        sanitised_profile_name, profile_name = self._get_profile_data()
        if sanitised_profile_name is None:
            return False

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

        self.component.send_data(ipc.RenderLayerRequest(list(self.get_render_layer_data())))
        return True

    def get_render_layer_data(self, file_path: str | None = None) -> Iterator[ipc.RenderLayer]:
        sanitised_profile_name, profile_name = self._get_profile_data()
        if sanitised_profile_name is None:
            return

        use_custom_width = self.ui.custom_width.isEnabled()
        use_custom_height = self.ui.custom_height.isEnabled()
        custom_width = self.ui.custom_width.value() if use_custom_width else None
        custom_height = self.ui.custom_height.value() if use_custom_height else None
        lock_aspect = self.ui.lock_aspect.isChecked()

        if file_path is None:
            width = self.ui.thumbnail.width()
            height = self.ui.thumbnail.height()

            # Account for collapsed splitters
            if not self.ui.horizontal_splitter.sizes()[1] and self.ui.horizontal_splitter.is_handle_visible():
                width += self.ui.horizontal_splitter.handleWidth()
            if not self.ui.vertical_splitter.sizes()[1] and self.ui.vertical_splitter.is_handle_visible():
                height += self.ui.vertical_splitter.handleWidth()

            if not lock_aspect and (use_custom_width or use_custom_height):
                # Set the aspect ratio to requested
                aspect_ratio = width / height
                if aspect_ratio > width / height:
                    height = round(width / aspect_ratio)
                else:
                    width = round(height * aspect_ratio)

            # Ensure resolutions aren't greater than requested
            if use_custom_width:
                width = min(width, custom_width)
            if use_custom_height:
                height = min(height, custom_height)

        else:
            width = custom_width
            height = custom_height

        old_layer = self._selected_layer

        for i in range(self.ui.layer_list.count(), 0, -1):
            item = self.ui.layer_list.item(i - 1)
            self._selected_layer = item.data(QtCore.Qt.ItemDataRole.UserRole)

            layer = ipc.RenderRequest(
                type=self.render_type,
                width=width,
                height=height,
                lock_aspect=lock_aspect,
                profile=sanitised_profile_name,
                file_path=file_path,
                colour_map=self.render_colour,
                padding=self.padding,
                sampling=self.ui.thumbnail_sampling.value(),
                contrast=self.contrast,
                clipping=self.clipping,
                blur=self.blur,
                linear=self.linear,
                invert=self.invert,
                show_left_clicks=self.show_left_clicks,
                show_middle_clicks=self.show_middle_clicks,
                show_right_clicks=self.show_right_clicks,
                show_count=self.ui.show_count.isChecked(),
                show_time=self.ui.show_time.isChecked(),
                interpolation_order=self.ui.interpolation_order.value(),
                layer_visible=item.checkState() == QtCore.Qt.CheckState.Checked,
            )

            yield ipc.RenderLayer(layer, self.selected_layer.blend_mode, self.selected_layer.channels, self.selected_layer.opacity)

        self._selected_layer = old_layer

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
            self.start_tracking()
        else:
            self.pause_tracking()

    def request_render(self) -> None:
        """Send a render request."""

        dialog = QtWidgets.QFileDialog()
        dialog.setAcceptMode(QtWidgets.QFileDialog.AcceptMode.AcceptSave)
        dialog.setNameFilters(['PNG Files (*.png)"'])
        dialog.setDefaultSuffix('png')

        match self.render_type:
            case ipc.RenderType.MouseMovement:
                name = 'Mouse Movement'
            case ipc.RenderType.MousePosition:
                name = 'Mouse Position'
            case ipc.RenderType.MouseSpeed:
                name = 'Mouse Speed'
            case ipc.RenderType.SingleClick:
                name = 'Mouse Clicks'
            case ipc.RenderType.DoubleClick:
                name = 'Mouse Double Clicks'
            case ipc.RenderType.HeldClick:
                name = 'Mouse Held Clicks'
            case ipc.RenderType.ThumbstickMovement:
                name = 'Gamepad Thumbstick Movement'
            case ipc.RenderType.ThumbstickPosition:
                name = 'Gamepad Thumbstick Position'
            case ipc.RenderType.ThumbstickSpeed:
                name = 'Gamepad Thumbstick Speed'
            case ipc.RenderType.KeyboardHeatmap:
                name = 'Keyboard Heatmap'
            case _:
                name = 'Data'

        sanitised_profile_name, profile_name = self._get_profile_data()
        if sanitised_profile_name is None or profile_name is None:
            return
        profile_safe = re.sub(r'[^\w_.)( -]', '', profile_name)

        # Get the default save folder
        image_dir = Path.home() / 'Pictures'
        if image_dir.exists():
            image_dir /= 'MouseTracks'
            if not image_dir.exists():
                image_dir.mkdir()

        # Get the correct profile elapsed time
        # It's only stored for the current profile, so load the data
        # from disk if the requested profile isn't current
        if self._is_loading_profile:
            try:
                _profile = TrackingProfile.load(get_filename(profile_name), metadata_only=True)
            except FileNotFoundError:
                elapsed_time = 0
            else:
                elapsed_time = _profile.elapsed
        else:
            elapsed_time = self.elapsed_time

        # Generate the default image name
        sort_key = f'{math.isqrt(round(elapsed_time / UPDATES_PER_SECOND)):05}'
        ticks_str = format_ticks(elapsed_time, UPDATES_PER_SECOND)
        image_dir /= f'{profile_safe} - {name} - {sort_key} - {ticks_str} ({self.render_colour})'

        file_path, accept = dialog.getSaveFileName(None, 'Save Image', str(image_dir), 'Image Files (*.png)')

        if accept:
            self.component.send_data(ipc.RenderLayerRequest(list(self.get_render_layer_data(file_path))))

    def thumbnail_render_check(self) -> None:
        """Check if the thumbnail should be re-rendered."""
        match self.render_type:
            # This does it every 10, 20, ..., 90, 100, 200, ..., 900, 1000, 2000, etc
            case ipc.RenderType.MouseMovement:
                count = self.cursor_data.counter
                update_frequency = min(20000, 10 ** int(math.log10(max(10, count))))
            # With speed it must be constant, doesn't work as well live
            case ipc.RenderType.MouseSpeed | ipc.RenderType.MousePosition:
                update_frequency = 50
                count = self.cursor_data.counter
            case ipc.RenderType.SingleClick | ipc.RenderType.DoubleClick:
                update_frequency = 1
                count = self.mouse_click_count
            case ipc.RenderType.HeldClick:
                update_frequency = 50
                count = self.mouse_held_count
            case ipc.RenderType.ThumbstickMovement:
                count = self.thumbstick_l_data.counter + self.thumbstick_r_data.counter
                update_frequency = min(20000, 10 ** int(math.log10(max(10, count))))
            case ipc.RenderType.ThumbstickSpeed | ipc.RenderType.ThumbstickPosition:
                count = self.thumbstick_l_data.counter + self.thumbstick_r_data.counter
                update_frequency = 50
            case ipc.RenderType.KeyboardHeatmap:
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
                if message.array.any():
                    height, width, channels = message.array.shape
                else:
                    height = width = channels = 0
                failed = width == height == 0

                target_height = round(height / (message.request.sampling or 1))
                target_width = round(width / (message.request.sampling or 1))

                # Draw the new pixmap
                if message.request.file_path is None:
                    self._timer_rendering.stop()
                    self.ui.thumbnail.hide_rendering_text()
                    self._last_thumbnail_time = int(time.time() * 10)

                    if failed:
                        self.ui.thumbnail.set_pixmap(QtGui.QPixmap())

                    else:
                        stride = channels * width
                        array = message.array

                        # Normalise down to 8 bit arrays
                        if array.dtype != np.uint8:
                            match message.array.dtype:
                                case np.uint16:
                                    array = message.array / 257
                                case np.uint32:
                                    array = message.array / (65537 * 257)
                                case np.uint64:
                                    array = message.array / (4294967297 * 65537 * 257)
                                case _:
                                    raise NotImplementedError(array.dtype)
                            array = array.round().astype(np.uint8)

                        match channels:
                            case 1:
                                image_format = QtGui.QImage.Format.Format_Grayscale8
                            case 3:
                                image_format = QtGui.QImage.Format.Format_RGB888
                            case 4:
                                image_format = QtGui.QImage.Format.Format_RGBA8888
                            case _:
                                raise NotImplementedError(channels)

                        image = QtGui.QImage(array.data, width, height, stride, image_format)

                        # Scale the QImage to fit the pixmap size
                        scaled_image = image.scaled(target_width, target_height, QtCore.Qt.AspectRatioMode.KeepAspectRatio, QtCore.Qt.TransformationMode.SmoothTransformation)
                        self.ui.thumbnail.set_pixmap(scaled_image)

                    self.pause_redraw -= 1

                    # Check if the flag was set that a new thumbnail was requested
                    if not self.pause_redraw and self._thumbnail_redraw_required:
                        self._request_thumbnail()
                        self._thumbnail_redraw_required = False

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
                if self.render_type == ipc.RenderType.MouseMovement:
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

                remapped = round(x * 1024 + 1024), round(-y * 1024 + 1024)
                if self.render_type == ipc.RenderType.ThumbstickMovement:
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
                    for sanitised_profile_name, profile_name in self._profile_names.items():
                        if profile_name == message.name:
                            self.request_profile_data(sanitised_profile_name)
                            break

            case ipc.ApplicationFocusChanged():
                self.update_focused_application(message.exe, message.title, message.tracked)

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
                    self._network_speed.set(message)

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
                widget_values = {
                    (self.ui.status_hub_state, self.ui.status_hub_queue): message.hub,
                    (self.ui.status_tracking_state, self.ui.status_tracking_queue): message.tracking,
                    (self.ui.status_processing_state, self.ui.status_processing_queue): message.processing,
                    (self.ui.status_gui_state, self.ui.status_gui_queue): message.gui,
                    (self.ui.status_app_state, self.ui.status_app_queue): message.app_detection,
                }

                for (status_widget, queue_widget), value in widget_values.items():
                    match self.state:
                        case ipc.TrackingState.Running:
                            if value < 5:
                                state = 'Running'
                            else:
                                state = 'Busy'
                        case ipc.TrackingState.Paused:
                            state = 'Paused'
                        case ipc.TrackingState.Stopped:
                            state = 'Stopped'
                        case _:
                            state = 'Unknown'
                    status_widget.setText(state)
                    queue_widget.setText(str(value))

            case ipc.InvalidConsole():
                self.ui.prefs_console.setEnabled(False)
                self.ui.prefs_console.setChecked(False)

            case ipc.ToggleConsole() if self.ui.prefs_console.isEnabled():
                self.ui.prefs_console.setChecked(message.show)

            # Load a legacy profile and switch to it
            case ipc.ImportProfile() | ipc.ImportLegacyProfile():
                sanitised_profile_name = sanitise_profile_name(message.name)
                self._profile_names[sanitised_profile_name] = message.name
                self._unsaved_profiles.add(sanitised_profile_name)
                self._redraw_profile_combobox()
                self.ui.current_profile.setCurrentIndex(tuple(self._profile_names).index(sanitised_profile_name))

            case ipc.FailedProfileImport():
                # Undo adding the profile
                sanitised_profile_name = sanitise_profile_name(message.source.name)
                del self._profile_names[sanitised_profile_name]
                self._unsaved_profiles.discard(sanitised_profile_name)
                self._redraw_profile_combobox()
                self.ui.auto_switch_profile.setChecked(True)
                self.profile_changed(self.ui.current_profile.currentIndex())

                # Show error message
                msg = QtWidgets.QMessageBox()
                msg.setIcon(QtWidgets.QMessageBox.Icon.Critical)
                msg.setWindowTitle('Failed Import')
                msg.setText(f'Failed to import "{message.source.path}" as a profile.')
                msg.exec()

            case ipc.ExportStatsSuccessful():
                msg = AutoCloseMessageBox(self)
                msg.setWindowTitle(f'Export Successful')
                msg.setText(f'"{message.source.path}" was successfully saved.')
                msg.setIcon(QtWidgets.QMessageBox.Icon.Information)
                msg.exec_with_timeout('Closing notification', GlobalConfig.export_notification_timeout)

            case ipc.ReloadAppList():
                self._last_app_reload_time = int(time.time() * 10)

            case ipc.SendPID():
                match message.source:
                    case ipc.Target.Hub:
                        self.ui.status_hub_pid.setText(str(message.pid))
                    case ipc.Target.Tracking:
                        self.ui.status_tracking_pid.setText(str(message.pid))
                    case ipc.Target.Processing:
                        self.ui.status_processing_pid.setText(str(message.pid))
                    case ipc.Target.GUI:
                        self.ui.status_gui_pid.setText(str(message.pid))
                    case ipc.Target.AppDetection:
                        self.ui.status_app_pid.setText(str(message.pid))

            case ipc.AllComponentsLoaded():
                self.on_app_ready()

            case ipc.ShowPopup():
                self.notify(message.content)

    @QtCore.Slot()
    def start_tracking(self) -> None:
        """Start/unpause the tracking."""
        self.notify(f'{self.windowTitle()} has resumed tracking.')
        self.cursor_data.position = get_cursor_pos()  # Prevent erroneous line jumps
        self.component.send_data(ipc.StartTracking())
        self.ui.save.setEnabled(True)
        self.ui.thumbnail_refresh.setEnabled(True)
        self.set_profile_modified_text()

    @QtCore.Slot()
    def pause_tracking(self) -> None:
        """Pause/unpause the tracking."""
        self.notify(f'{self.windowTitle()} has paused tracking.')
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
        """What to do when the tray icon is activated.

        Note that each OS handles this differently. On Windows, a double
        click is a `DoubleClick` where as on Linux it's `Trigger`. A
        right click on windows is `Context`, and it's not supported for
        Linux. The context menu handling has been moved to the menus
        `aboutToShow` method instead which is cross platform.
        """
        match reason:
            case (QtWidgets.QSystemTrayIcon.ActivationReason.DoubleClick  # Windows
                  | QtWidgets.QSystemTrayIcon.ActivationReason.Trigger):  # Linux
                self.load_from_tray()

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

    @QtCore.Slot()
    def update_tray_menu(self) -> None:
        """Update the visible items in the tray context menu."""
        self.ui.tray_show.setVisible(not self.isVisible())
        self.ui.tray_hide.setVisible(self.isVisible())

        # Determine if the debug menu should be visible
        modifiers = QtGui.QGuiApplication.queryKeyboardModifiers()
        shift_held = modifiers & QtCore.Qt.KeyboardModifier.ShiftModifier
        self.ui.menu_debug.menuAction().setVisible(bool(shift_held))

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
            self._timer_tip.start(600000)

        self.set_tip_timer_state(True)

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

        self.set_tip_timer_state(False)

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

        # If the window is not yet ready then just close
        if not self._window_ready:
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

    def handle_session_shutdown(self, manager: QtGui.QSessionManager) -> None:
        """Force the app to close when the system is shutting down.
        At this point, the queues are closed, so nothing more can be
        done.
        """
        self.shut_down(force=True)
        manager.release()

    def update_track_data(self, data: MapData, position: tuple[int, int]) -> None:
        data.distance += calculate_distance(position, data.position)

        # Update the saved data
        data.counter += 1
        data.position = position

        # Check if array compression has been done
        if data.counter > COMPRESSION_THRESHOLD:
            data.counter = round(data.counter / COMPRESSION_FACTOR)

    @property
    def is_live(self) -> bool:
        """Determine if the visible data is live."""
        sanitised_profile_name, profile_name = self._get_profile_data()
        if sanitised_profile_name is None:
            return False
        return sanitised_profile_name == sanitise_profile_name(self.current_profile.name)

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

        # Convert logical to physical
        if old_position is not None:
            old_position = self.monitor_data.coordinate(old_position)
        if new_position is not None:
            new_position = self.monitor_data.coordinate(new_position)

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

            # Avoid drawing if resolution option isn't ticked
            if not self._resolution_options.get(current_monitor, True):
                continue

            width_multiplier = (size.width() - 1) / current_monitor[0]
            height_multiplier = (size.height() - 1) / current_monitor[1]

            # Downscale the pixel to match the pixmap
            x = round(pixel[0] * width_multiplier)
            y = round(pixel[1] * height_multiplier)
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
        sanitised_profile_name, profile_name = self._get_profile_data()
        if sanitised_profile_name is None or profile_name is None:
            return None

        msg = QtWidgets.QMessageBox(self)
        msg.setIcon(QtWidgets.QMessageBox.Icon.Warning)
        msg.setWindowTitle('Delete Keyboard Data')
        msg.setText(f'Are you sure you want to delete all mouse data for {profile_name}?\n'
                    'This involves the movement, click and scroll data.\n'
                    'It will not trigger an autosave, but it cannot be undone.')
        msg.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No)
        msg.setDefaultButton(QtWidgets.QMessageBox.StandardButton.No)
        msg.setEscapeButton(QtWidgets.QMessageBox.StandardButton.No)

        if msg.exec() == QtWidgets.QMessageBox.StandardButton.Yes:
            self._delete_mouse_pressed = True
            self.handle_delete_button_visibility()
            self.component.send_data(ipc.DeleteMouseData(sanitised_profile_name))
            self.mark_profiles_unsaved(profile_name)
            self._redraw_profile_combobox()
            self.request_profile_data(sanitised_profile_name)

    def delete_keyboard(self) -> None:
        """Request deletion of keyboard data for the current profile."""
        sanitised_profile_name, profile_name = self._get_profile_data()
        if sanitised_profile_name is None or profile_name is None:
            return None

        msg = QtWidgets.QMessageBox(self)
        msg.setIcon(QtWidgets.QMessageBox.Icon.Warning)
        msg.setWindowTitle('Delete Keyboard Data')
        msg.setText(f'Are you sure you want to delete all keyboard data for {profile_name}?\n'
                    'It will not trigger an autosave, but it cannot be undone.')
        msg.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No)
        msg.setDefaultButton(QtWidgets.QMessageBox.StandardButton.No)
        msg.setEscapeButton(QtWidgets.QMessageBox.StandardButton.No)

        if msg.exec() == QtWidgets.QMessageBox.StandardButton.Yes:
            self._delete_keyboard_pressed = True
            self.handle_delete_button_visibility()
            self.component.send_data(ipc.DeleteKeyboardData(sanitised_profile_name))
            self.mark_profiles_unsaved(profile_name)
            self._redraw_profile_combobox()
            self.request_profile_data(sanitised_profile_name)

    def delete_gamepad(self) -> None:
        """Request deletion of gamepad data for the current profile."""
        sanitised_profile_name, profile_name = self._get_profile_data()
        if sanitised_profile_name is None or profile_name is None:
            return None

        msg = QtWidgets.QMessageBox(self)
        msg.setIcon(QtWidgets.QMessageBox.Icon.Warning)
        msg.setWindowTitle('Delete Keyboard Data')
        msg.setText(f'Are you sure you want to delete all gamepad data for {profile_name}?\n'
                    'This involves both the buttons and the thumbstick maps.\n'
                    'It will not trigger an autosave, but it cannot be undone.')
        msg.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No)
        msg.setDefaultButton(QtWidgets.QMessageBox.StandardButton.No)
        msg.setEscapeButton(QtWidgets.QMessageBox.StandardButton.No)

        if msg.exec() == QtWidgets.QMessageBox.StandardButton.Yes:
            self._delete_gamepad_pressed = True
            self.handle_delete_button_visibility()
            self.component.send_data(ipc.DeleteGamepadData(sanitised_profile_name))
            self.mark_profiles_unsaved(profile_name)
            self._redraw_profile_combobox()
            self.request_profile_data(sanitised_profile_name)

    def delete_network(self) -> None:
        """Request deletion of network data for the current profile."""
        sanitised_profile_name, profile_name = self._get_profile_data()
        if sanitised_profile_name is None or profile_name is None:
            return None

        msg = QtWidgets.QMessageBox(self)
        msg.setIcon(QtWidgets.QMessageBox.Icon.Warning)
        msg.setWindowTitle('Delete Network Data')
        msg.setText(f'Are you sure you want to delete all upload and download data for {profile_name}?\n'
                    'It will not trigger an autosave, but it cannot be undone.')
        msg.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No)
        msg.setDefaultButton(QtWidgets.QMessageBox.StandardButton.No)
        msg.setEscapeButton(QtWidgets.QMessageBox.StandardButton.No)

        if msg.exec() == QtWidgets.QMessageBox.StandardButton.Yes:
            self._delete_network_pressed = True
            self.handle_delete_button_visibility()
            self.component.send_data(ipc.DeleteNetworkData(sanitised_profile_name))
            self.mark_profiles_unsaved(profile_name)
            self._redraw_profile_combobox()
            self.request_profile_data(sanitised_profile_name)

    def delete_profile(self) -> None:
        """Delete the selected profile."""
        sanitised_profile_name, profile_name = self._get_profile_data()
        if sanitised_profile_name is None or profile_name is None:
            return None

        msg = QtWidgets.QMessageBox(self)
        msg.setIcon(QtWidgets.QMessageBox.Icon.Critical)
        msg.setWindowTitle('Delete Profile')
        msg.setText(f'Are you sure you want to delete all data for {profile_name}?\n'
                    'This action cannot be undone.')
        msg.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No)
        msg.setDefaultButton(QtWidgets.QMessageBox.StandardButton.No)
        msg.setEscapeButton(QtWidgets.QMessageBox.StandardButton.No)

        if msg.exec() == QtWidgets.QMessageBox.StandardButton.Yes:
            self.component.send_data(ipc.DeleteProfile(sanitised_profile_name))

            # Only remove from list if it's not the currently selected profile
            if sanitised_profile_name != sanitise_profile_name(self._current_profile.name):
                self.mark_profiles_saved(profile_name)
                del self._profile_names[sanitised_profile_name]
                self._unsaved_profiles.discard(sanitised_profile_name)

            self._redraw_profile_combobox()
            self.profile_changed(0)

    @QtCore.Slot(QtCore.Qt.CheckState)
    def toggle_profile_mouse_tracking(self, state: QtCore.Qt.CheckState) -> None:
        if not self.ui.track_mouse.isEnabled():
            return
        sanitised_profile_name, profile_name = self._get_profile_data()
        if sanitised_profile_name is None:
            return

        enable = state == QtCore.Qt.CheckState.Checked.value
        self.component.send_data(ipc.SetProfileMouseTracking(sanitised_profile_name, enable))

    @QtCore.Slot(QtCore.Qt.CheckState)
    def toggle_profile_keyboard_tracking(self, state: QtCore.Qt.CheckState) -> None:
        if not self.ui.track_keyboard.isEnabled():
            return
        sanitised_profile_name, profile_name = self._get_profile_data()
        if sanitised_profile_name is None:
            return

        enable = state == QtCore.Qt.CheckState.Checked.value
        self.component.send_data(ipc.SetProfileKeyboardTracking(sanitised_profile_name, enable))

    @QtCore.Slot(QtCore.Qt.CheckState)
    def toggle_profile_gamepad_tracking(self, state: QtCore.Qt.CheckState) -> None:
        if not self.ui.track_gamepad.isEnabled():
            return
        sanitised_profile_name, profile_name = self._get_profile_data()
        if sanitised_profile_name is None:
            return

        enable = state == QtCore.Qt.CheckState.Checked.value
        self.component.send_data(ipc.SetProfileGamepadTracking(sanitised_profile_name, enable))

    @QtCore.Slot(QtCore.Qt.CheckState)
    def toggle_profile_network_tracking(self, state: QtCore.Qt.CheckState) -> None:
        if not self.ui.track_network.isEnabled():
            return
        sanitised_profile_name, profile_name = self._get_profile_data()
        if sanitised_profile_name is None:
            return

        enable = state == QtCore.Qt.CheckState.Checked.value
        self.component.send_data(ipc.SetProfileNetworkTracking(sanitised_profile_name, enable))

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

    @QtCore.Slot(bool)
    def set_app_detection_disabled(self, value: bool) -> None:
        self.component.send_data(ipc.DebugDisableAppDetection(value))

    @QtCore.Slot(bool)
    def set_monitor_check_disabled(self, value: bool) -> None:
        self.component.send_data(ipc.DebugDisableMonitorCheck(value))

    def mark_profiles_saved(self, *profile_names: str) -> None:
        """Mark profiles as saved."""
        for sanitised_profile_name, profile_name in self._profile_names.items():
            if profile_name in profile_names:
                self._unsaved_profiles.discard(sanitised_profile_name)
        self.set_profile_modified_text()

    def mark_profiles_unsaved(self, *profile_names: str) -> None:
        """Mark profiles as unsaved."""
        for sanitised_profile_name, profile_name in self._profile_names.items():
            if profile_name in profile_names:
                self._unsaved_profiles.add(sanitised_profile_name)
        self.set_profile_modified_text()

    def set_profile_modified_text(self) -> None:
        """Set the text if the profile has been modified."""
        sanitised_profile_name, profile_name = self._get_profile_data()
        if sanitised_profile_name is not None and sanitised_profile_name in self._unsaved_profiles:
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
            if args and Path(args[0]).resolve() == Path(SYS_EXECUTABLE).resolve():
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
        is_thumbstick = self.render_type in (ipc.RenderType.ThumbstickMovement, ipc.RenderType.ThumbstickSpeed, ipc.RenderType.ThumbstickPosition)
        is_keyboard = self.render_type == ipc.RenderType.KeyboardHeatmap

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
        self.ui.invert.setVisible(show_advanced and not is_keyboard)

        self.ui.resolution_group.setVisible(show_advanced and not is_keyboard)
        self.ui.layer_group.setVisible(show_advanced and not is_keyboard)

    def notify(self, message: str) -> None:
        """Show a notification.
        If the tray messages are not available, a popup will be shown
        instead. If called on startup, then the message will be queue
        until the window is ready.
        """
        if not self._window_ready:
            self._startup_notify_queue.append(message)
        elif self.tray is None or not self.tray.supportsMessages():
            if self.isVisible():
                msg = QtWidgets.QMessageBox(self)
                msg.setWindowTitle(self.windowTitle())
                msg.setIcon(QtWidgets.QMessageBox.Icon.Information)
                msg.setText(message)
                msg.exec()
        else:
            self.tray.showMessage(self.windowTitle(), message, self.tray.icon(), 2000)

    @QtCore.Slot()
    def import_profile(self) -> None:
        """Prompt the user to import a profile.
        Legacy profiles are supported, but will need to be given a name.
        A check is done to avoid name clashes.
        """
        # Get the default legacy location if available
        documents_path = _get_docs_folder()
        default_dir = documents_path / 'Mouse Tracks' / 'Data'
        if not default_dir.exists():
            if PROFILE_DIR.exists():
                default_dir = PROFILE_DIR
            else:
                default_dir = documents_path

        # Select the profile
        path, filter = QtWidgets.QFileDialog.getOpenFileName(self, 'Select Profile',
                                                             str(default_dir),
                                                             'MouseTracks Profile (*.mtk)')
        if not path:
            return

        is_legacy = False
        profile_name = TrackingProfile.get_name(path)
        if profile_name is None:
            profile_name = QtCore.QFileInfo(path).baseName()
            is_legacy = True

        while True:
            profile_name, accept = QtWidgets.QInputDialog.getText(self, 'Profile Name', 'Enter the name of the profile:',
                                                                  QtWidgets.QLineEdit.EchoMode.Normal, profile_name)
            if not accept:
                return
            if not profile_name.strip():
                continue
            elif TYPE_CHECKING:
                assert isinstance(profile_name, str)

            # Check if the profile already exists
            if not PROFILE_DIR.exists():
                break
            if os.path.basename(get_filename(profile_name)) not in os.listdir(PROFILE_DIR):
                if sanitise_profile_name(profile_name) not in self._profile_names:
                    break

            # Show a warning
            msg = QtWidgets.QMessageBox()
            msg.setIcon(QtWidgets.QMessageBox.Icon.Warning)
            msg.setWindowTitle('Warning')
            msg.setText('This profile already exists.\n\n'
                        'To avoid accidental overwrites, '
                        'please delete the existing profile or choose a new name.')
            msg.exec()

        # Send the request
        if is_legacy:
            self.component.send_data(ipc.ImportLegacyProfile(profile_name, path))
        else:
            self.component.send_data(ipc.ImportProfile(profile_name, path))

    @QtCore.Slot()
    def export_mouse_stats(self) -> None:
        """Export the mouse statistics."""
        dialog = QtWidgets.QFileDialog()
        dialog.setAcceptMode(QtWidgets.QFileDialog.AcceptMode.AcceptSave)
        dialog.setNameFilters(['CSV Files (*.csv)"'])
        dialog.setDefaultSuffix('csv')

        sanitised_profile_name, profile_name = self._get_profile_data()
        if sanitised_profile_name is None or profile_name is None:
            return
        profile_safe = re.sub(r'[^\w_.)( -]', '', profile_name)
        export_dir = _get_docs_folder() / f'[{format_ticks(self.elapsed_time)}] {profile_safe} - Mouse Stats.csv'

        file_path, accept = dialog.getSaveFileName(self, 'Save Mouse Stats', str(export_dir), 'CSV Files (*.csv)')
        if accept:
            self.component.send_data(ipc.ExportMouseStats(sanitised_profile_name, file_path))

    @QtCore.Slot()
    def export_keyboard_stats(self) -> None:
        """Export the keyboard statistics."""
        dialog = QtWidgets.QFileDialog()
        dialog.setAcceptMode(QtWidgets.QFileDialog.AcceptMode.AcceptSave)
        dialog.setNameFilters(['CSV Files (*.csv)"'])
        dialog.setDefaultSuffix('csv')

        sanitised_profile_name, profile_name = self._get_profile_data()
        if sanitised_profile_name is None or profile_name is None:
            return
        profile_safe = re.sub(r'[^\w_.)( -]', '', profile_name)
        export_dir = _get_docs_folder() / f'[{format_ticks(self.elapsed_time)}] {profile_safe} - Keyboard Stats.csv'

        file_path, accept = dialog.getSaveFileName(self, 'Save Keyboard Stats', str(export_dir), 'CSV Files (*.csv)')
        if accept:
            self.component.send_data(ipc.ExportKeyboardStats(sanitised_profile_name, file_path))

    @QtCore.Slot()
    def export_gamepad_stats(self) -> None:
        """Export the gamepad statistics."""
        dialog = QtWidgets.QFileDialog()
        dialog.setAcceptMode(QtWidgets.QFileDialog.AcceptMode.AcceptSave)
        dialog.setNameFilters(['CSV Files (*.csv)"'])
        dialog.setDefaultSuffix('csv')

        sanitised_profile_name, profile_name = self._get_profile_data()
        if sanitised_profile_name is None or profile_name is None:
            return
        profile_safe = re.sub(r'[^\w_.)( -]', '', profile_name)
        export_dir = _get_docs_folder() / f'[{format_ticks(self.elapsed_time)}] {profile_safe} - Gamepad Stats.csv'

        file_path, accept = dialog.getSaveFileName(self, 'Save Gamepad Stats', str(export_dir), 'CSV Files (*.csv)')
        if accept:
            self.component.send_data(ipc.ExportGamepadStats(sanitised_profile_name, file_path))

    @QtCore.Slot()
    def export_network_stats(self) -> None:
        """Export the network statistics."""
        dialog = QtWidgets.QFileDialog()
        dialog.setAcceptMode(QtWidgets.QFileDialog.AcceptMode.AcceptSave)
        dialog.setNameFilters(['CSV Files (*.csv)"'])
        dialog.setDefaultSuffix('csv')

        sanitised_profile_name, profile_name = self._get_profile_data()
        if sanitised_profile_name is None or profile_name is None:
            return
        profile_safe = re.sub(r'[^\w_.)( -]', '', profile_name)
        export_dir = _get_docs_folder() / f'[{format_ticks(self.elapsed_time)}] {profile_safe} - Network Stats.csv'

        file_path, accept = dialog.getSaveFileName(self, 'Save Network Stats', str(export_dir), 'CSV Files (*.csv)')
        if accept:
            self.component.send_data(ipc.ExportNetworkStats(sanitised_profile_name, file_path))

    @QtCore.Slot()
    def export_daily_stats(self) -> None:
        """Export the daily statistics."""
        dialog = QtWidgets.QFileDialog()
        dialog.setAcceptMode(QtWidgets.QFileDialog.AcceptMode.AcceptSave)
        dialog.setNameFilters(['CSV Files (*.csv)"'])
        dialog.setDefaultSuffix('csv')

        sanitised_profile_name, profile_name = self._get_profile_data()
        if sanitised_profile_name is None or profile_name is None:
            return
        profile_safe = re.sub(r'[^\w_.)( -]', '', profile_name)
        export_dir = _get_docs_folder() / f'[{format_ticks(self.elapsed_time)}] {profile_safe} - Daily Stats.csv'

        file_path, accept = dialog.getSaveFileName(self, 'Save Daily Stats', str(export_dir), 'CSV Files (*.csv)')
        if accept:
            self.component.send_data(ipc.ExportDailyStats(sanitised_profile_name, file_path))

    @property
    def selected_layer(self) -> LayerOption:
        """Get the selected layer data."""
        return self._layers[self._selected_layer]

    def add_render_layer(self, reselect: bool = True) -> QtWidgets.QListWidgetItem:
        """Add a new disabled render layer."""
        item = QtWidgets.QListWidgetItem()
        item.setCheckState(QtCore.Qt.CheckState.Unchecked)
        item.setData(QtCore.Qt.ItemDataRole.UserRole, self._layer_counter)

        selected_items = self.ui.layer_list.selectedItems()
        self.ui.layer_list.insertItem(0, item)
        if reselect and selected_items:
            if selected_items:
                for previous in selected_items:
                    previous.setSelected(True)
        else:
            item.setSelected(True)

        self._layers[self._layer_counter] = LayerOption(ipc.RenderType.MouseMovement, BlendMode.Normal, Channel.RGBA)
        self._layer_counter += 1
        self.update_layer_item_name(item)
        return item

    @QtCore.Slot()
    def delete_render_layer(self) -> None:
        """Delete the selected render layer."""
        for item in self.ui.layer_list.selectedItems():
            if self.ui.layer_list.count() <= 1:
                msg = QtWidgets.QMessageBox(self)
                msg.setWindowTitle('Error')
                msg.setIcon(QtWidgets.QMessageBox.Icon.Warning)
                msg.setText('Failed to remove layer, no other layers exit.')
                msg.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Ok)
                msg.exec()

            else:
                self.ui.layer_list.takeItem(self.ui.layer_list.row(item))

    @QtCore.Slot(QtWidgets.QListWidgetItem, QtWidgets.QListWidgetItem)
    def selected_layer_changed(self, current: QtWidgets.QListWidgetItem,
                               previous: QtWidgets.QListWidgetItem) -> None:
        """Update widgets when the selected layer changes."""
        if current == previous or current is None:
            return

        self._is_updating_layer_options = True
        try:
            self._selected_layer = current.data(QtCore.Qt.ItemDataRole.UserRole)
            layer = self._layers[self._selected_layer]

            # Set the render type which will update the other widgets
            idx = self.ui.map_type.findData(layer.render_type)
            if idx == self.ui.map_type.currentIndex():
                self.render_type_changed(idx)
            else:
                self.ui.map_type.setCurrentIndex(idx)

            # Set the layer blending
            idx = self.ui.layer_blending.findData(layer.blend_mode)
            self.ui.layer_blending.setCurrentIndex(idx)

            # Set the channels
            self.ui.layer_r.setChecked(layer.channels & Channel.R)
            self.ui.layer_g.setChecked(layer.channels & Channel.G)
            self.ui.layer_b.setChecked(layer.channels & Channel.B)
            self.ui.layer_a.setChecked(layer.channels & Channel.A)

            # Set the opacity
            self.ui.layer_opacity.setValue(layer.opacity)

        finally:
            self._is_updating_layer_options = False

        self.request_thumbnail()

    @QtCore.Slot(QtWidgets.QListWidgetItem)
    def selected_layer_toggled(self, item: QtWidgets.QListWidgetItem) -> None:
        """Update when a layer is enabled or disabled."""
        self.request_thumbnail()

    @QtCore.Slot(QtCore.QModelIndex, int, int, QtCore.QModelIndex, int)
    def selected_layer_moved(self, srcParent: QtCore.QModelIndex, start: int, end: int,
                             dstParent: QtCore.QModelIndex, dstRow: int) -> None:
        """Update when a layer is removed."""
        self.request_thumbnail()

    @QtCore.Slot(int)
    def layer_blend_mode_changed(self, idx: int) -> None:
        """Update when the blend mode is changed for the current layer."""
        if self._is_updating_layer_options:
            return
        self.selected_layer.blend_mode = self.ui.layer_blending.itemData(idx)
        self.request_thumbnail()
        self.update_layer_item_name()

    @QtCore.Slot()
    def layer_channel_changed(self) -> None:
        """Update when the channels are changed for the current layer."""
        if self._is_updating_layer_options:
            return
        channels = 0
        if self.ui.layer_r.isChecked():
            channels |= Channel.R
        if self.ui.layer_g.isChecked():
            channels |= Channel.G
        if self.ui.layer_b.isChecked():
            channels |= Channel.B
        if self.ui.layer_a.isChecked():
            channels |= Channel.A
        self.selected_layer.channels = Channel(channels)
        self.request_thumbnail()
        self.update_layer_item_name()

    @QtCore.Slot(int)
    def layer_opacity_changed(self, value: int) -> None:
        """Update when the opacity is changed for the current layer."""
        if self._is_updating_layer_options:
            return
        self.selected_layer.opacity = value
        self.request_thumbnail()
        self.update_layer_item_name()

    @QtCore.Slot()
    def move_layer_up(self) -> None:
        """Move the selected layer up if possible."""
        for item in self.ui.layer_list.selectedItems():
            row = self.ui.layer_list.row(item)
            if row <= 0:
                continue

            self.ui.layer_list.takeItem(row)
            self.ui.layer_list.insertItem(row - 1, item)
            self.ui.layer_list.setCurrentItem(item)

    @QtCore.Slot()
    def move_layer_down(self) -> None:
        """Move the selected layer down if possible."""
        for item in self.ui.layer_list.selectedItems():
            row = self.ui.layer_list.row(item)
            if row < 0 or row >= self.ui.layer_list.count() - 1:
                continue

            self.ui.layer_list.takeItem(row)
            self.ui.layer_list.insertItem(row + 1, item)
            self.ui.layer_list.setCurrentItem(item)

    @QtCore.Slot(int)
    def layer_preset_chosen(self, idx: int) -> None:
        """Load in a layer preset.
        This is hardcoded for now as the current system wouldn't work
        well with loading from a file.
        """
        if not idx:
            return

        match self.ui.layer_presets.currentText():
            case 'Reset':
                self.ui.layer_list.clear()
                layer_0 = self.add_render_layer()
                layer_0.setCheckState(QtCore.Qt.CheckState.Checked)

            case 'Heatmap Overlay':
                self.ui.layer_list.clear()
                layer_0 = self.add_render_layer()
                layer_0.setCheckState(QtCore.Qt.CheckState.Checked)
                layer_1 = self.add_render_layer()
                layer_1.setCheckState(QtCore.Qt.CheckState.Checked)

                self._selected_layer = layer_0.data(QtCore.Qt.ItemDataRole.UserRole)
                self.selected_layer.render_type = ipc.RenderType.MouseMovement

                self._selected_layer = layer_1.data(QtCore.Qt.ItemDataRole.UserRole)
                self.selected_layer.opacity = 50
                self.selected_layer.render_type = ipc.RenderType.SingleClick
                self.selected_layer.blend_mode = BlendMode.LuminanceMask
                self.selected_layer.clipping.heatmap = 0.01
                self.selected_layer.contrast.heatmap = 1.5

            case 'Heatmap Tracks':
                self.ui.layer_list.clear()
                layer_0 = self.add_render_layer()
                layer_0.setCheckState(QtCore.Qt.CheckState.Checked)
                layer_1 = self.add_render_layer()
                layer_1.setCheckState(QtCore.Qt.CheckState.Checked)

                self._selected_layer = layer_0.data(QtCore.Qt.ItemDataRole.UserRole)
                self.selected_layer.render_type = ipc.RenderType.MouseMovement
                self.selected_layer.render_colour.movement = 'Chalk'

                self._selected_layer = layer_1.data(QtCore.Qt.ItemDataRole.UserRole)
                self.selected_layer.blend_mode = BlendMode.Multiply
                self.selected_layer.render_type = ipc.RenderType.MousePosition
                self.selected_layer.render_colour.heatmap = 'Inferno'
                self.selected_layer.blur.heatmap = 0.001

            case 'Alpha Multiply':
                self.ui.layer_list.clear()
                layer_0 = self.add_render_layer()
                layer_0.setCheckState(QtCore.Qt.CheckState.Checked)
                layer_1 = self.add_render_layer()
                layer_1.setCheckState(QtCore.Qt.CheckState.Checked)

                self._selected_layer = layer_0.data(QtCore.Qt.ItemDataRole.UserRole)
                self.selected_layer.render_type = ipc.RenderType.MouseMovement

                self._selected_layer = layer_1.data(QtCore.Qt.ItemDataRole.UserRole)
                self.selected_layer.render_type = ipc.RenderType.MousePosition
                self.selected_layer.blend_mode = BlendMode.Multiply
                self.selected_layer.channels = Channel.A
                self.selected_layer.render_colour.heatmap = 'TransparentWhiteToWhite'
                self.selected_layer.blur.heatmap = 0
                self.selected_layer.clipping.heatmap = 0.85
                self.selected_layer.contrast.heatmap = 0.5

            case 'Urban Grass':
                self.ui.layer_list.clear()
                layer_0 = self.add_render_layer()
                layer_0.setCheckState(QtCore.Qt.CheckState.Checked)
                layer_1 = self.add_render_layer()
                layer_1.setCheckState(QtCore.Qt.CheckState.Checked)

                self._selected_layer = layer_0.data(QtCore.Qt.ItemDataRole.UserRole)
                self.selected_layer.render_type = ipc.RenderType.MouseMovement
                self.selected_layer.render_colour.movement = 'Chalk'

                self._selected_layer = layer_1.data(QtCore.Qt.ItemDataRole.UserRole)
                self.selected_layer.render_type = ipc.RenderType.MouseSpeed
                self.selected_layer.render_colour.speed = 'TransparentBlackToBlackToGreen'

            case 'Eraser':
                self.ui.layer_list.clear()
                layer_0 = self.add_render_layer()
                layer_0.setCheckState(QtCore.Qt.CheckState.Checked)
                layer_1 = self.add_render_layer()
                layer_1.setCheckState(QtCore.Qt.CheckState.Checked)

                self._selected_layer = layer_0.data(QtCore.Qt.ItemDataRole.UserRole)
                self.selected_layer.render_type = ipc.RenderType.MouseMovement
                self.selected_layer.render_colour.movement = 'Graphite'

                self._selected_layer = layer_1.data(QtCore.Qt.ItemDataRole.UserRole)
                self.selected_layer.render_type = ipc.RenderType.SingleClick
                self.selected_layer.blend_mode = BlendMode.Subtract
                self.selected_layer.render_colour.heatmap = 'TransparentWhiteToWhite'
                self.selected_layer.channels = Channel.A
                self.selected_layer.clipping.heatmap = 0.2
                self.selected_layer.contrast.heatmap = 1.5

            case 'Plasma':
                self.ui.layer_list.clear()
                layer_0 = self.add_render_layer()
                layer_0.setCheckState(QtCore.Qt.CheckState.Checked)
                layer_1 = self.add_render_layer()
                layer_1.setCheckState(QtCore.Qt.CheckState.Checked)

                self._selected_layer = layer_0.data(QtCore.Qt.ItemDataRole.UserRole)
                self.selected_layer.render_type = ipc.RenderType.MouseMovement
                self.selected_layer.render_colour.movement = 'Demon'

                self._selected_layer = layer_1.data(QtCore.Qt.ItemDataRole.UserRole)
                self.selected_layer.render_type = ipc.RenderType.SingleClick
                self.selected_layer.blend_mode = BlendMode.HardLight
                self.selected_layer.render_colour.heatmap = 'Riptide'
                self.selected_layer.clipping.heatmap = 0.01
                self.selected_layer.blur.heatmap = 0.02

            case 'RGB Clicks':
                self.ui.layer_list.clear()
                layer_0 = self.add_render_layer()
                layer_0.setCheckState(QtCore.Qt.CheckState.Checked)
                layer_1 = self.add_render_layer()
                layer_1.setCheckState(QtCore.Qt.CheckState.Checked)
                layer_2 = self.add_render_layer()
                layer_2.setCheckState(QtCore.Qt.CheckState.Checked)

                self._selected_layer = layer_0.data(QtCore.Qt.ItemDataRole.UserRole)
                self.selected_layer.blend_mode = BlendMode.Screen
                self.selected_layer.render_type = ipc.RenderType.SingleClick
                self.selected_layer.render_colour.heatmap = 'Chalk'
                self.selected_layer.show_middle_clicks = False
                self.selected_layer.show_right_clicks = False
                self.selected_layer.channels = Channel.R | Channel.A

                self._selected_layer = layer_1.data(QtCore.Qt.ItemDataRole.UserRole)
                self.selected_layer.blend_mode = BlendMode.Screen
                self.selected_layer.render_type = ipc.RenderType.SingleClick
                self.selected_layer.render_colour.heatmap = 'Chalk'
                self.selected_layer.show_left_clicks = False
                self.selected_layer.show_right_clicks = False
                self.selected_layer.channels = Channel.G | Channel.A

                self._selected_layer = layer_2.data(QtCore.Qt.ItemDataRole.UserRole)
                self.selected_layer.blend_mode = BlendMode.Screen
                self.selected_layer.render_type = ipc.RenderType.SingleClick
                self.selected_layer.render_colour.heatmap = 'Chalk'
                self.selected_layer.show_left_clicks = False
                self.selected_layer.show_middle_clicks = False
                self.selected_layer.channels = Channel.B | Channel.A

        self._selected_layer = 0
        self.ui.layer_presets.setCurrentIndex(0)
        self.ui.layer_list.setCurrentItem(layer_0)

        for item in map(self.ui.layer_list.item, range(self.ui.layer_list.count())):
            self.update_layer_item_name(item)

    def update_layer_item_name(self, item: QtWidgets.QListWidgetItem | None = None) -> None:
        """Generate the name of each layer."""
        if item is None:
            item = self.ui.layer_list.selectedItems()[0]

        # Read the layer from the given item
        layer = item.data(QtCore.Qt.ItemDataRole.UserRole)
        data = self._layers[layer]

        tyoe_name = self.ui.map_type.itemText(self.ui.map_type.findData(data.render_type)).split(']', 1)[1][1:]

        # Override the type name if any click options are disabled
        if data.render_type in (ipc.RenderType.SingleClick, ipc.RenderType.DoubleClick, ipc.RenderType.HeldClick):
            enabled = []
            if data.show_left_clicks:
                enabled.append('LMB')
            if data.show_middle_clicks:
                enabled.append('MMB')
            if data.show_right_clicks:
                enabled.append('RMB')
            if enabled and len(enabled) < 3:
                tyoe_name = '|'.join(enabled)

        # Override the type name if any thumbstick options are disabled
        if data.render_type in (ipc.RenderType.ThumbstickMovement, ipc.RenderType.ThumbstickPosition, ipc.RenderType.ThumbstickSpeed):
            enabled = []
            if data.show_left_clicks:
                enabled.append('Left')
            if data.show_right_clicks:
                enabled.append('Right')
            if enabled and len(enabled) < 2:
                tyoe_name = f'{enabled[0]} {tyoe_name}'

        # Generate the name
        name_parts: list[Any] = [
            f'Layer {layer}',
            tyoe_name,
            data.blend_mode.name,
            f'{data.opacity}%',
            Channel(data.channels).name,
        ]
        item.setText(' | '.join(map(str, name_parts)))

    def update_focused_application(self, exe: str, title: str, tracked: bool) -> None:
        """Update the focused application text."""
        self.ui.stat_app_exe.setText(os.path.basename(exe))
        self.ui.stat_app_title.setText(title)
        self.ui.stat_app_tracked.setText('Yes' if tracked else 'No')
