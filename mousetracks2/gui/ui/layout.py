# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'layout.ui'
##
## Created by: Qt User Interface Compiler version 6.8.0
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QAction, QBrush, QColor, QConicalGradient,
    QCursor, QFont, QFontDatabase, QGradient,
    QIcon, QImage, QKeySequence, QLinearGradient,
    QPainter, QPalette, QPixmap, QRadialGradient,
    QTransform)
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QCheckBox, QComboBox,
    QDoubleSpinBox, QGridLayout, QGroupBox, QHBoxLayout,
    QLabel, QListWidget, QListWidgetItem, QMainWindow,
    QMenu, QMenuBar, QPushButton, QRadioButton,
    QScrollArea, QScrollBar, QSizePolicy, QSpacerItem,
    QSpinBox, QStatusBar, QTabWidget, QVBoxLayout,
    QWidget)

from mousetracks2.gui.widgets import (ResizableImage, Splitter)

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(1060, 613)
        self.file_save = QAction(MainWindow)
        self.file_save.setObjectName(u"file_save")
        self.file_import = QAction(MainWindow)
        self.file_import.setObjectName(u"file_import")
        self.menu_exit = QAction(MainWindow)
        self.menu_exit.setObjectName(u"menu_exit")
        self.menu_allow_minimise = QAction(MainWindow)
        self.menu_allow_minimise.setObjectName(u"menu_allow_minimise")
        self.menu_allow_minimise.setCheckable(True)
        self.menu_allow_minimise.setChecked(True)
        self.file_tracking_start = QAction(MainWindow)
        self.file_tracking_start.setObjectName(u"file_tracking_start")
        self.file_tracking_pause = QAction(MainWindow)
        self.file_tracking_pause.setObjectName(u"file_tracking_pause")
        self.link_github = QAction(MainWindow)
        self.link_github.setObjectName(u"link_github")
        self.link_github.setProperty(u"website", QUrl(u"https://github.com/huntfx/MouseTracks"))
        self.link_reddit = QAction(MainWindow)
        self.link_reddit.setObjectName(u"link_reddit")
        self.link_reddit.setProperty(u"website", QUrl(u"https://www.reddit.com/r/MouseTracks"))
        self.link_facebook = QAction(MainWindow)
        self.link_facebook.setObjectName(u"link_facebook")
        self.link_facebook.setProperty(u"website", QUrl(u"https://www.facebook.com/MouseTracksApp"))
        self.tray_exit = QAction(MainWindow)
        self.tray_exit.setObjectName(u"tray_exit")
        self.tray_show = QAction(MainWindow)
        self.tray_show.setObjectName(u"tray_show")
        self.tray_hide = QAction(MainWindow)
        self.tray_hide.setObjectName(u"tray_hide")
        self.prefs_track_keyboard = QAction(MainWindow)
        self.prefs_track_keyboard.setObjectName(u"prefs_track_keyboard")
        self.prefs_track_keyboard.setCheckable(True)
        self.prefs_track_keyboard.setChecked(True)
        self.prefs_track_gamepad = QAction(MainWindow)
        self.prefs_track_gamepad.setObjectName(u"prefs_track_gamepad")
        self.prefs_track_gamepad.setCheckable(True)
        self.prefs_track_gamepad.setChecked(True)
        self.prefs_track_mouse = QAction(MainWindow)
        self.prefs_track_mouse.setObjectName(u"prefs_track_mouse")
        self.prefs_track_mouse.setCheckable(True)
        self.prefs_track_mouse.setChecked(True)
        self.prefs_autostart = QAction(MainWindow)
        self.prefs_autostart.setObjectName(u"prefs_autostart")
        self.prefs_autostart.setCheckable(True)
        self.prefs_automin = QAction(MainWindow)
        self.prefs_automin.setObjectName(u"prefs_automin")
        self.prefs_automin.setCheckable(True)
        self.prefs_console = QAction(MainWindow)
        self.prefs_console.setObjectName(u"prefs_console")
        self.prefs_console.setCheckable(True)
        self.prefs_console.setChecked(True)
        self.full_screen = QAction(MainWindow)
        self.full_screen.setObjectName(u"full_screen")
        self.full_screen.setCheckable(True)
        self.prefs_track_network = QAction(MainWindow)
        self.prefs_track_network.setObjectName(u"prefs_track_network")
        self.prefs_track_network.setCheckable(True)
        self.prefs_track_network.setChecked(True)
        self.always_on_top = QAction(MainWindow)
        self.always_on_top.setObjectName(u"always_on_top")
        self.always_on_top.setCheckable(True)
        self.debug_raise_hub = QAction(MainWindow)
        self.debug_raise_hub.setObjectName(u"debug_raise_hub")
        self.debug_state_running = QAction(MainWindow)
        self.debug_state_running.setObjectName(u"debug_state_running")
        self.debug_state_paused = QAction(MainWindow)
        self.debug_state_paused.setObjectName(u"debug_state_paused")
        self.debug_state_stopped = QAction(MainWindow)
        self.debug_state_stopped.setObjectName(u"debug_state_stopped")
        self.debug_raise_tracking = QAction(MainWindow)
        self.debug_raise_tracking.setObjectName(u"debug_raise_tracking")
        self.debug_raise_processing = QAction(MainWindow)
        self.debug_raise_processing.setObjectName(u"debug_raise_processing")
        self.debug_raise_gui = QAction(MainWindow)
        self.debug_raise_gui.setObjectName(u"debug_raise_gui")
        self.debug_raise_app = QAction(MainWindow)
        self.debug_raise_app.setObjectName(u"debug_raise_app")
        self.export_mouse_stats = QAction(MainWindow)
        self.export_mouse_stats.setObjectName(u"export_mouse_stats")
        self.export_keyboard_stats = QAction(MainWindow)
        self.export_keyboard_stats.setObjectName(u"export_keyboard_stats")
        self.export_network_stats = QAction(MainWindow)
        self.export_network_stats.setObjectName(u"export_network_stats")
        self.export_gamepad_stats = QAction(MainWindow)
        self.export_gamepad_stats.setObjectName(u"export_gamepad_stats")
        self.export_daily_stats = QAction(MainWindow)
        self.export_daily_stats.setObjectName(u"export_daily_stats")
        self.about = QAction(MainWindow)
        self.about.setObjectName(u"about")
        self.tray_about = QAction(MainWindow)
        self.tray_about.setObjectName(u"tray_about")
        self.tray_app_add = QAction(MainWindow)
        self.tray_app_add.setObjectName(u"tray_app_add")
        self.tray_donate = QAction(MainWindow)
        self.tray_donate.setObjectName(u"tray_donate")
        self.link_donate = QAction(MainWindow)
        self.link_donate.setObjectName(u"link_donate")
        self.link_donate.setProperty(u"website", QUrl(u"https://github.com/huntfx/MouseTracks/wiki/Donate"))
        self.debug_pause_app = QAction(MainWindow)
        self.debug_pause_app.setObjectName(u"debug_pause_app")
        self.debug_pause_app.setCheckable(True)
        self.debug_pause_monitor = QAction(MainWindow)
        self.debug_pause_monitor.setObjectName(u"debug_pause_monitor")
        self.debug_pause_monitor.setCheckable(True)
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.main_layout = QVBoxLayout(self.centralwidget)
        self.main_layout.setObjectName(u"main_layout")
        self.vertical_splitter = Splitter(self.centralwidget)
        self.vertical_splitter.setObjectName(u"vertical_splitter")
        self.vertical_splitter.setOrientation(Qt.Orientation.Vertical)
        self.horizontal_splitter = Splitter(self.vertical_splitter)
        self.horizontal_splitter.setObjectName(u"horizontal_splitter")
        self.horizontal_splitter.setOrientation(Qt.Orientation.Horizontal)
        self.widget = QWidget(self.horizontal_splitter)
        self.widget.setObjectName(u"widget")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(2)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.widget.sizePolicy().hasHeightForWidth())
        self.widget.setSizePolicy(sizePolicy)
        self.render_layout = QVBoxLayout(self.widget)
        self.render_layout.setObjectName(u"render_layout")
        self.thumbnail = ResizableImage(self.widget)
        self.thumbnail.setObjectName(u"thumbnail")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.thumbnail.sizePolicy().hasHeightForWidth())
        self.thumbnail.setSizePolicy(sizePolicy1)

        self.render_layout.addWidget(self.thumbnail)

        self.horizontal_splitter.addWidget(self.widget)
        self.tab_options = QTabWidget(self.horizontal_splitter)
        self.tab_options.setObjectName(u"tab_options")
        sizePolicy2 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.tab_options.sizePolicy().hasHeightForWidth())
        self.tab_options.setSizePolicy(sizePolicy2)
        self.tab_options.setMinimumSize(QSize(300, 0))
        self.tab = QWidget()
        self.tab.setObjectName(u"tab")
        self.verticalLayout_2 = QVBoxLayout(self.tab)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.scrollArea = QScrollArea(self.tab)
        self.scrollArea.setObjectName(u"scrollArea")
        self.scrollArea.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName(u"scrollAreaWidgetContents")
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 311, 1327))
        self.verticalLayout_3 = QVBoxLayout(self.scrollAreaWidgetContents)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.groupBox_2 = QGroupBox(self.scrollAreaWidgetContents)
        self.groupBox_2.setObjectName(u"groupBox_2")
        self.verticalLayout_9 = QVBoxLayout(self.groupBox_2)
        self.verticalLayout_9.setObjectName(u"verticalLayout_9")
        self.current_profile = QComboBox(self.groupBox_2)
        self.current_profile.addItem("")
        self.current_profile.addItem("")
        self.current_profile.addItem("")
        self.current_profile.setObjectName(u"current_profile")
        sizePolicy3 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        sizePolicy3.setHorizontalStretch(0)
        sizePolicy3.setVerticalStretch(0)
        sizePolicy3.setHeightForWidth(self.current_profile.sizePolicy().hasHeightForWidth())
        self.current_profile.setSizePolicy(sizePolicy3)

        self.verticalLayout_9.addWidget(self.current_profile)

        self.auto_switch_profile = QCheckBox(self.groupBox_2)
        self.auto_switch_profile.setObjectName(u"auto_switch_profile")
        self.auto_switch_profile.setChecked(True)

        self.verticalLayout_9.addWidget(self.auto_switch_profile)


        self.verticalLayout_3.addWidget(self.groupBox_2)

        self.resolution_group = QGroupBox(self.scrollAreaWidgetContents)
        self.resolution_group.setObjectName(u"resolution_group")
        self.gridLayout_7 = QGridLayout(self.resolution_group)
        self.gridLayout_7.setObjectName(u"gridLayout_7")
        self.custom_height_label = QLabel(self.resolution_group)
        self.custom_height_label.setObjectName(u"custom_height_label")
        sizePolicy1.setHeightForWidth(self.custom_height_label.sizePolicy().hasHeightForWidth())
        self.custom_height_label.setSizePolicy(sizePolicy1)
        self.custom_height_label.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout_7.addWidget(self.custom_height_label, 1, 0, 1, 1)

        self.lock_aspect = QCheckBox(self.resolution_group)
        self.lock_aspect.setObjectName(u"lock_aspect")
        self.lock_aspect.setChecked(True)

        self.gridLayout_7.addWidget(self.lock_aspect, 2, 1, 1, 1)

        self.horizontalLayout_8 = QHBoxLayout()
        self.horizontalLayout_8.setObjectName(u"horizontalLayout_8")
        self.custom_height = QSpinBox(self.resolution_group)
        self.custom_height.setObjectName(u"custom_height")
        self.custom_height.setEnabled(False)
        sizePolicy3.setHeightForWidth(self.custom_height.sizePolicy().hasHeightForWidth())
        self.custom_height.setSizePolicy(sizePolicy3)
        self.custom_height.setSuffix(u"px")
        self.custom_height.setMinimum(1)
        self.custom_height.setMaximum(999999)
        self.custom_height.setSingleStep(9)
        self.custom_height.setValue(1080)

        self.horizontalLayout_8.addWidget(self.custom_height)

        self.enable_custom_height = QCheckBox(self.resolution_group)
        self.enable_custom_height.setObjectName(u"enable_custom_height")

        self.horizontalLayout_8.addWidget(self.enable_custom_height)


        self.gridLayout_7.addLayout(self.horizontalLayout_8, 1, 1, 1, 1)

        self.horizontalLayout_5 = QHBoxLayout()
        self.horizontalLayout_5.setObjectName(u"horizontalLayout_5")
        self.custom_width = QSpinBox(self.resolution_group)
        self.custom_width.setObjectName(u"custom_width")
        self.custom_width.setEnabled(False)
        sizePolicy3.setHeightForWidth(self.custom_width.sizePolicy().hasHeightForWidth())
        self.custom_width.setSizePolicy(sizePolicy3)
        self.custom_width.setSuffix(u"px")
        self.custom_width.setMinimum(1)
        self.custom_width.setMaximum(999999)
        self.custom_width.setSingleStep(16)
        self.custom_width.setValue(1920)

        self.horizontalLayout_5.addWidget(self.custom_width)

        self.enable_custom_width = QCheckBox(self.resolution_group)
        self.enable_custom_width.setObjectName(u"enable_custom_width")

        self.horizontalLayout_5.addWidget(self.enable_custom_width)


        self.gridLayout_7.addLayout(self.horizontalLayout_5, 0, 1, 1, 1)

        self.custom_width_label = QLabel(self.resolution_group)
        self.custom_width_label.setObjectName(u"custom_width_label")
        sizePolicy1.setHeightForWidth(self.custom_width_label.sizePolicy().hasHeightForWidth())
        self.custom_width_label.setSizePolicy(sizePolicy1)
        self.custom_width_label.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout_7.addWidget(self.custom_width_label, 0, 0, 1, 1)


        self.verticalLayout_3.addWidget(self.resolution_group)

        self.groupBox_3 = QGroupBox(self.scrollAreaWidgetContents)
        self.groupBox_3.setObjectName(u"groupBox_3")
        self.gridLayout_6 = QGridLayout(self.groupBox_3)
        self.gridLayout_6.setObjectName(u"gridLayout_6")
        self.horizontalLayout_4 = QHBoxLayout()
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.show_left_clicks = QCheckBox(self.groupBox_3)
        self.show_left_clicks.setObjectName(u"show_left_clicks")
        self.show_left_clicks.setChecked(True)

        self.horizontalLayout_4.addWidget(self.show_left_clicks)

        self.show_middle_clicks = QCheckBox(self.groupBox_3)
        self.show_middle_clicks.setObjectName(u"show_middle_clicks")
        self.show_middle_clicks.setChecked(True)

        self.horizontalLayout_4.addWidget(self.show_middle_clicks)

        self.show_right_clicks = QCheckBox(self.groupBox_3)
        self.show_right_clicks.setObjectName(u"show_right_clicks")
        self.show_right_clicks.setChecked(True)

        self.horizontalLayout_4.addWidget(self.show_right_clicks)


        self.gridLayout_6.addLayout(self.horizontalLayout_4, 1, 0, 1, 1)

        self.map_type = QComboBox(self.groupBox_3)
        self.map_type.setObjectName(u"map_type")

        self.gridLayout_6.addWidget(self.map_type, 0, 0, 1, 1)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.show_count = QRadioButton(self.groupBox_3)
        self.show_count.setObjectName(u"show_count")
        self.show_count.setChecked(True)

        self.horizontalLayout_2.addWidget(self.show_count)

        self.show_time = QRadioButton(self.groupBox_3)
        self.show_time.setObjectName(u"show_time")

        self.horizontalLayout_2.addWidget(self.show_time)


        self.gridLayout_6.addLayout(self.horizontalLayout_2, 2, 0, 1, 1)


        self.verticalLayout_3.addWidget(self.groupBox_3)

        self.groupBox_5 = QGroupBox(self.scrollAreaWidgetContents)
        self.groupBox_5.setObjectName(u"groupBox_5")
        self.verticalLayout_4 = QVBoxLayout(self.groupBox_5)
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.gridLayout_12 = QGridLayout()
        self.gridLayout_12.setObjectName(u"gridLayout_12")
        self.thumbnail_sampling = QSpinBox(self.groupBox_5)
        self.thumbnail_sampling.setObjectName(u"thumbnail_sampling")
        self.thumbnail_sampling.setMinimum(0)
        self.thumbnail_sampling.setMaximum(8)
        self.thumbnail_sampling.setValue(0)

        self.gridLayout_12.addWidget(self.thumbnail_sampling, 14, 1, 1, 1)

        self.contrast = QDoubleSpinBox(self.groupBox_5)
        self.contrast.setObjectName(u"contrast")
        sizePolicy4 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        sizePolicy4.setHorizontalStretch(0)
        sizePolicy4.setVerticalStretch(0)
        sizePolicy4.setHeightForWidth(self.contrast.sizePolicy().hasHeightForWidth())
        self.contrast.setSizePolicy(sizePolicy4)
        self.contrast.setDecimals(3)
        self.contrast.setMinimum(0.050000000000000)
        self.contrast.setMaximum(99.950000000000003)
        self.contrast.setSingleStep(0.050000000000000)
        self.contrast.setValue(1.000000000000000)

        self.gridLayout_12.addWidget(self.contrast, 8, 1, 1, 1)

        self.sampling_label = QLabel(self.groupBox_5)
        self.sampling_label.setObjectName(u"sampling_label")
        sizePolicy1.setHeightForWidth(self.sampling_label.sizePolicy().hasHeightForWidth())
        self.sampling_label.setSizePolicy(sizePolicy1)
        self.sampling_label.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout_12.addWidget(self.sampling_label, 13, 0, 1, 1)

        self.label_14 = QLabel(self.groupBox_5)
        self.label_14.setObjectName(u"label_14")
        self.label_14.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout_12.addWidget(self.label_14, 11, 0, 1, 1)

        self.label_16 = QLabel(self.groupBox_5)
        self.label_16.setObjectName(u"label_16")
        sizePolicy1.setHeightForWidth(self.label_16.sizePolicy().hasHeightForWidth())
        self.label_16.setSizePolicy(sizePolicy1)
        self.label_16.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout_12.addWidget(self.label_16, 10, 0, 1, 1)

        self.colour_option = QComboBox(self.groupBox_5)
        self.colour_option.addItem("")
        self.colour_option.addItem("")
        self.colour_option.addItem("")
        self.colour_option.setObjectName(u"colour_option")
        sizePolicy3.setHeightForWidth(self.colour_option.sizePolicy().hasHeightForWidth())
        self.colour_option.setSizePolicy(sizePolicy3)
        self.colour_option.setEditable(True)

        self.gridLayout_12.addWidget(self.colour_option, 0, 1, 1, 1)

        self.sampling = QSpinBox(self.groupBox_5)
        self.sampling.setObjectName(u"sampling")
        sizePolicy3.setHeightForWidth(self.sampling.sizePolicy().hasHeightForWidth())
        self.sampling.setSizePolicy(sizePolicy3)
        self.sampling.setMinimum(0)
        self.sampling.setMaximum(8)
        self.sampling.setValue(4)

        self.gridLayout_12.addWidget(self.sampling, 13, 1, 1, 1)

        self.label_18 = QLabel(self.groupBox_5)
        self.label_18.setObjectName(u"label_18")
        self.label_18.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout_12.addWidget(self.label_18, 12, 0, 1, 1)

        self.label_31 = QLabel(self.groupBox_5)
        self.label_31.setObjectName(u"label_31")
        self.label_31.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout_12.addWidget(self.label_31, 15, 0, 1, 1)

        self.contrast_label = QLabel(self.groupBox_5)
        self.contrast_label.setObjectName(u"contrast_label")
        self.contrast_label.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout_12.addWidget(self.contrast_label, 8, 0, 1, 1)

        self.padding = QSpinBox(self.groupBox_5)
        self.padding.setObjectName(u"padding")
        sizePolicy3.setHeightForWidth(self.padding.sizePolicy().hasHeightForWidth())
        self.padding.setSizePolicy(sizePolicy3)
        self.padding.setMaximum(4096)
        self.padding.setSingleStep(8)

        self.gridLayout_12.addWidget(self.padding, 10, 1, 1, 1)

        self.linear = QCheckBox(self.groupBox_5)
        self.linear.setObjectName(u"linear")

        self.gridLayout_12.addWidget(self.linear, 2, 1, 1, 1)

        self.interpolation_order = QSpinBox(self.groupBox_5)
        self.interpolation_order.setObjectName(u"interpolation_order")
        self.interpolation_order.setMaximum(5)

        self.gridLayout_12.addWidget(self.interpolation_order, 15, 1, 1, 1)

        self.clipping = QDoubleSpinBox(self.groupBox_5)
        self.clipping.setObjectName(u"clipping")
        self.clipping.setDecimals(8)
        self.clipping.setMaximum(100.000000000000000)
        self.clipping.setSingleStep(0.000100000000000)

        self.gridLayout_12.addWidget(self.clipping, 11, 1, 1, 1)

        self.label_28 = QLabel(self.groupBox_5)
        self.label_28.setObjectName(u"label_28")
        self.label_28.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout_12.addWidget(self.label_28, 14, 0, 1, 1)

        self.blur = QDoubleSpinBox(self.groupBox_5)
        self.blur.setObjectName(u"blur")
        self.blur.setDecimals(8)
        self.blur.setMaximum(1.000000000000000)
        self.blur.setSingleStep(0.000500000000000)
        self.blur.setValue(0.012500000000000)

        self.gridLayout_12.addWidget(self.blur, 12, 1, 1, 1)

        self.label_24 = QLabel(self.groupBox_5)
        self.label_24.setObjectName(u"label_24")
        self.label_24.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout_12.addWidget(self.label_24, 0, 0, 1, 1)

        self.invert = QCheckBox(self.groupBox_5)
        self.invert.setObjectName(u"invert")

        self.gridLayout_12.addWidget(self.invert, 1, 1, 1, 1)


        self.verticalLayout_4.addLayout(self.gridLayout_12)


        self.verticalLayout_3.addWidget(self.groupBox_5)

        self.layer_group = QGroupBox(self.scrollAreaWidgetContents)
        self.layer_group.setObjectName(u"layer_group")
        self.verticalLayout_14 = QVBoxLayout(self.layer_group)
        self.verticalLayout_14.setObjectName(u"verticalLayout_14")
        self.layer_presets = QComboBox(self.layer_group)
        self.layer_presets.addItem("")
        self.layer_presets.setObjectName(u"layer_presets")
        self.layer_presets.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self.verticalLayout_14.addWidget(self.layer_presets)

        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.layer_list = QListWidget(self.layer_group)
        __qlistwidgetitem = QListWidgetItem(self.layer_list)
        __qlistwidgetitem.setCheckState(Qt.Unchecked);
        __qlistwidgetitem1 = QListWidgetItem(self.layer_list)
        __qlistwidgetitem1.setCheckState(Qt.Checked);
        self.layer_list.setObjectName(u"layer_list")
        self.layer_list.setMaximumSize(QSize(16777215, 114))
        self.layer_list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)

        self.horizontalLayout_3.addWidget(self.layer_list)

        self.verticalLayout_17 = QVBoxLayout()
        self.verticalLayout_17.setObjectName(u"verticalLayout_17")
        self.layer_add = QPushButton(self.layer_group)
        self.layer_add.setObjectName(u"layer_add")
        self.layer_add.setMaximumSize(QSize(24, 24))

        self.verticalLayout_17.addWidget(self.layer_add)

        self.layer_remove = QPushButton(self.layer_group)
        self.layer_remove.setObjectName(u"layer_remove")
        self.layer_remove.setMaximumSize(QSize(24, 24))

        self.verticalLayout_17.addWidget(self.layer_remove)

        self.layer_up = QPushButton(self.layer_group)
        self.layer_up.setObjectName(u"layer_up")
        self.layer_up.setMaximumSize(QSize(24, 24))

        self.verticalLayout_17.addWidget(self.layer_up)

        self.layer_down = QPushButton(self.layer_group)
        self.layer_down.setObjectName(u"layer_down")
        self.layer_down.setMaximumSize(QSize(24, 24))

        self.verticalLayout_17.addWidget(self.layer_down)


        self.horizontalLayout_3.addLayout(self.verticalLayout_17)


        self.verticalLayout_14.addLayout(self.horizontalLayout_3)

        self.gridLayout_9 = QGridLayout()
        self.gridLayout_9.setObjectName(u"gridLayout_9")
        self.label_33 = QLabel(self.layer_group)
        self.label_33.setObjectName(u"label_33")
        self.label_33.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout_9.addWidget(self.label_33, 1, 0, 1, 1)

        self.horizontalLayout_10 = QHBoxLayout()
        self.horizontalLayout_10.setObjectName(u"horizontalLayout_10")
        self.layer_r = QCheckBox(self.layer_group)
        self.layer_r.setObjectName(u"layer_r")
        self.layer_r.setChecked(True)

        self.horizontalLayout_10.addWidget(self.layer_r)

        self.layer_g = QCheckBox(self.layer_group)
        self.layer_g.setObjectName(u"layer_g")
        self.layer_g.setChecked(True)

        self.horizontalLayout_10.addWidget(self.layer_g)

        self.layer_b = QCheckBox(self.layer_group)
        self.layer_b.setObjectName(u"layer_b")
        self.layer_b.setChecked(True)

        self.horizontalLayout_10.addWidget(self.layer_b)

        self.layer_a = QCheckBox(self.layer_group)
        self.layer_a.setObjectName(u"layer_a")
        self.layer_a.setChecked(True)

        self.horizontalLayout_10.addWidget(self.layer_a)


        self.gridLayout_9.addLayout(self.horizontalLayout_10, 2, 1, 1, 1)

        self.layer_blending = QComboBox(self.layer_group)
        self.layer_blending.setObjectName(u"layer_blending")

        self.gridLayout_9.addWidget(self.layer_blending, 1, 1, 1, 1)

        self.layer_opacity = QSpinBox(self.layer_group)
        self.layer_opacity.setObjectName(u"layer_opacity")
        self.layer_opacity.setMaximum(100)
        self.layer_opacity.setSingleStep(10)
        self.layer_opacity.setValue(100)

        self.gridLayout_9.addWidget(self.layer_opacity, 0, 1, 1, 1)

        self.label_34 = QLabel(self.layer_group)
        self.label_34.setObjectName(u"label_34")
        self.label_34.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout_9.addWidget(self.label_34, 2, 0, 1, 1)

        self.label_32 = QLabel(self.layer_group)
        self.label_32.setObjectName(u"label_32")
        self.label_32.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout_9.addWidget(self.label_32, 0, 0, 1, 1)


        self.verticalLayout_14.addLayout(self.gridLayout_9)


        self.verticalLayout_3.addWidget(self.layer_group)

        self.groupBox_9 = QGroupBox(self.scrollAreaWidgetContents)
        self.groupBox_9.setObjectName(u"groupBox_9")
        self.gridLayout_3 = QGridLayout(self.groupBox_9)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.label_9 = QLabel(self.groupBox_9)
        self.label_9.setObjectName(u"label_9")
        self.label_9.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout_3.addWidget(self.label_9, 1, 0, 1, 1)

        self.label_11 = QLabel(self.groupBox_9)
        self.label_11.setObjectName(u"label_11")
        self.label_11.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout_3.addWidget(self.label_11, 5, 0, 1, 1)

        self.stat_active = QLabel(self.groupBox_9)
        self.stat_active.setObjectName(u"stat_active")

        self.gridLayout_3.addWidget(self.stat_active, 6, 1, 1, 1)

        self.label_8 = QLabel(self.groupBox_9)
        self.label_8.setObjectName(u"label_8")
        self.label_8.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout_3.addWidget(self.label_8, 9, 0, 1, 1)

        self.stat_clicks = QLabel(self.groupBox_9)
        self.stat_clicks.setObjectName(u"stat_clicks")

        self.gridLayout_3.addWidget(self.stat_clicks, 0, 1, 1, 1)

        self.stat_scroll = QLabel(self.groupBox_9)
        self.stat_scroll.setObjectName(u"stat_scroll")

        self.gridLayout_3.addWidget(self.stat_scroll, 1, 1, 1, 1)

        self.label_20 = QLabel(self.groupBox_9)
        self.label_20.setObjectName(u"label_20")
        self.label_20.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout_3.addWidget(self.label_20, 2, 0, 1, 1)

        self.label_22 = QLabel(self.groupBox_9)
        self.label_22.setObjectName(u"label_22")
        self.label_22.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout_3.addWidget(self.label_22, 6, 0, 1, 1)

        self.stat_elapsed = QLabel(self.groupBox_9)
        self.stat_elapsed.setObjectName(u"stat_elapsed")

        self.gridLayout_3.addWidget(self.stat_elapsed, 5, 1, 1, 1)

        self.label_21 = QLabel(self.groupBox_9)
        self.label_21.setObjectName(u"label_21")
        self.label_21.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout_3.addWidget(self.label_21, 0, 0, 1, 1)

        self.stat_keys = QLabel(self.groupBox_9)
        self.stat_keys.setObjectName(u"stat_keys")

        self.gridLayout_3.addWidget(self.stat_keys, 2, 1, 1, 1)

        self.stat_upload_total = QLabel(self.groupBox_9)
        self.stat_upload_total.setObjectName(u"stat_upload_total")

        self.gridLayout_3.addWidget(self.stat_upload_total, 9, 1, 1, 1)

        self.stat_inactive = QLabel(self.groupBox_9)
        self.stat_inactive.setObjectName(u"stat_inactive")

        self.gridLayout_3.addWidget(self.stat_inactive, 7, 1, 1, 1)

        self.stat_download_total = QLabel(self.groupBox_9)
        self.stat_download_total.setObjectName(u"stat_download_total")

        self.gridLayout_3.addWidget(self.stat_download_total, 8, 1, 1, 1)

        self.stat_buttons = QLabel(self.groupBox_9)
        self.stat_buttons.setObjectName(u"stat_buttons")

        self.gridLayout_3.addWidget(self.stat_buttons, 3, 1, 1, 1)

        self.label_19 = QLabel(self.groupBox_9)
        self.label_19.setObjectName(u"label_19")
        self.label_19.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout_3.addWidget(self.label_19, 4, 0, 1, 1)

        self.stat_distance = QLabel(self.groupBox_9)
        self.stat_distance.setObjectName(u"stat_distance")

        self.gridLayout_3.addWidget(self.stat_distance, 4, 1, 1, 1)

        self.label_4 = QLabel(self.groupBox_9)
        self.label_4.setObjectName(u"label_4")
        self.label_4.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout_3.addWidget(self.label_4, 8, 0, 1, 1)

        self.label_29 = QLabel(self.groupBox_9)
        self.label_29.setObjectName(u"label_29")
        self.label_29.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout_3.addWidget(self.label_29, 10, 0, 1, 1)

        self.label_23 = QLabel(self.groupBox_9)
        self.label_23.setObjectName(u"label_23")
        self.label_23.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout_3.addWidget(self.label_23, 7, 0, 1, 1)

        self.label = QLabel(self.groupBox_9)
        self.label.setObjectName(u"label")
        self.label.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout_3.addWidget(self.label, 3, 0, 1, 1)

        self.label_30 = QLabel(self.groupBox_9)
        self.label_30.setObjectName(u"label_30")
        self.label_30.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout_3.addWidget(self.label_30, 11, 0, 1, 1)

        self.stat_download_current = QLabel(self.groupBox_9)
        self.stat_download_current.setObjectName(u"stat_download_current")

        self.gridLayout_3.addWidget(self.stat_download_current, 10, 1, 1, 1)

        self.stat_upload_current = QLabel(self.groupBox_9)
        self.stat_upload_current.setObjectName(u"stat_upload_current")

        self.gridLayout_3.addWidget(self.stat_upload_current, 11, 1, 1, 1)


        self.verticalLayout_3.addWidget(self.groupBox_9)

        self.record_history = QGroupBox(self.scrollAreaWidgetContents)
        self.record_history.setObjectName(u"record_history")
        self.record_history.setEnabled(False)
        self.record_history.setCheckable(True)
        self.record_history.setChecked(False)
        self.verticalLayout_12 = QVBoxLayout(self.record_history)
        self.verticalLayout_12.setObjectName(u"verticalLayout_12")
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.label_7 = QLabel(self.record_history)
        self.label_7.setObjectName(u"label_7")

        self.horizontalLayout.addWidget(self.label_7)

        self.history_length = QSpinBox(self.record_history)
        self.history_length.setObjectName(u"history_length")
        self.history_length.setValue(2)

        self.horizontalLayout.addWidget(self.history_length)


        self.verticalLayout_12.addLayout(self.horizontalLayout)

        self.history_current = QScrollBar(self.record_history)
        self.history_current.setObjectName(u"history_current")
        self.history_current.setMaximum(3600)
        self.history_current.setValue(3600)
        self.history_current.setOrientation(Qt.Orientation.Horizontal)

        self.verticalLayout_12.addWidget(self.history_current)


        self.verticalLayout_3.addWidget(self.record_history)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_3.addItem(self.verticalSpacer)

        self.scrollArea.setWidget(self.scrollAreaWidgetContents)

        self.verticalLayout_2.addWidget(self.scrollArea)

        self.tip = QLabel(self.tab)
        self.tip.setObjectName(u"tip")
        self.tip.setWordWrap(True)

        self.verticalLayout_2.addWidget(self.tip)

        self.horizontalLayout_9 = QHBoxLayout()
        self.horizontalLayout_9.setObjectName(u"horizontalLayout_9")
        self.save_render = QPushButton(self.tab)
        self.save_render.setObjectName(u"save_render")
        sizePolicy3.setHeightForWidth(self.save_render.sizePolicy().hasHeightForWidth())
        self.save_render.setSizePolicy(sizePolicy3)

        self.horizontalLayout_9.addWidget(self.save_render)

        self.show_advanced = QCheckBox(self.tab)
        self.show_advanced.setObjectName(u"show_advanced")
        self.show_advanced.setChecked(True)

        self.horizontalLayout_9.addWidget(self.show_advanced)


        self.verticalLayout_2.addLayout(self.horizontalLayout_9)

        self.tab_options.addTab(self.tab, "")
        self.tab_profile_options = QWidget()
        self.tab_profile_options.setObjectName(u"tab_profile_options")
        self.verticalLayout_15 = QVBoxLayout(self.tab_profile_options)
        self.verticalLayout_15.setObjectName(u"verticalLayout_15")
        self.scrollArea_2 = QScrollArea(self.tab_profile_options)
        self.scrollArea_2.setObjectName(u"scrollArea_2")
        self.scrollArea_2.setWidgetResizable(True)
        self.scrollAreaWidgetContents_2 = QWidget()
        self.scrollAreaWidgetContents_2.setObjectName(u"scrollAreaWidgetContents_2")
        self.scrollAreaWidgetContents_2.setGeometry(QRect(0, 0, 311, 654))
        self.verticalLayout_13 = QVBoxLayout(self.scrollAreaWidgetContents_2)
        self.verticalLayout_13.setObjectName(u"verticalLayout_13")
        self.opts_status = QGroupBox(self.scrollAreaWidgetContents_2)
        self.opts_status.setObjectName(u"opts_status")
        self.gridLayout = QGridLayout(self.opts_status)
        self.gridLayout.setObjectName(u"gridLayout")
        self.horizontalLayout_6 = QHBoxLayout()
        self.horizontalLayout_6.setObjectName(u"horizontalLayout_6")
        self.profile_modified = QLabel(self.opts_status)
        self.profile_modified.setObjectName(u"profile_modified")

        self.horizontalLayout_6.addWidget(self.profile_modified)

        self.profile_save = QPushButton(self.opts_status)
        self.profile_save.setObjectName(u"profile_save")

        self.horizontalLayout_6.addWidget(self.profile_save)


        self.gridLayout.addLayout(self.horizontalLayout_6, 1, 1, 1, 1)

        self.label_13 = QLabel(self.opts_status)
        self.label_13.setObjectName(u"label_13")
        self.label_13.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout.addWidget(self.label_13, 1, 0, 1, 1)


        self.verticalLayout_13.addWidget(self.opts_status)

        self.opts_resolution = QGroupBox(self.scrollAreaWidgetContents_2)
        self.opts_resolution.setObjectName(u"opts_resolution")
        self.verticalLayout_6 = QVBoxLayout(self.opts_resolution)
        self.verticalLayout_6.setObjectName(u"verticalLayout_6")
        self.label_17 = QLabel(self.opts_resolution)
        self.label_17.setObjectName(u"label_17")
        self.label_17.setWordWrap(True)

        self.verticalLayout_6.addWidget(self.label_17)

        self.profile_resolutions = QGridLayout()
        self.profile_resolutions.setObjectName(u"profile_resolutions")
        self.label_15 = QLabel(self.opts_resolution)
        self.label_15.setObjectName(u"label_15")

        self.profile_resolutions.addWidget(self.label_15, 1, 1, 1, 1)

        self.checkBox_2 = QCheckBox(self.opts_resolution)
        self.checkBox_2.setObjectName(u"checkBox_2")
        self.checkBox_2.setChecked(True)

        self.profile_resolutions.addWidget(self.checkBox_2, 1, 0, 1, 1)

        self.checkBox = QCheckBox(self.opts_resolution)
        self.checkBox.setObjectName(u"checkBox")
        self.checkBox.setChecked(True)

        self.profile_resolutions.addWidget(self.checkBox, 0, 0, 1, 1)

        self.label_2 = QLabel(self.opts_resolution)
        self.label_2.setObjectName(u"label_2")

        self.profile_resolutions.addWidget(self.label_2, 0, 1, 1, 1)

        self.checkBox_4 = QCheckBox(self.opts_resolution)
        self.checkBox_4.setObjectName(u"checkBox_4")
        self.checkBox_4.setChecked(True)

        self.profile_resolutions.addWidget(self.checkBox_4, 2, 0, 1, 1)

        self.label_3 = QLabel(self.opts_resolution)
        self.label_3.setObjectName(u"label_3")

        self.profile_resolutions.addWidget(self.label_3, 2, 1, 1, 1)


        self.verticalLayout_6.addLayout(self.profile_resolutions)


        self.verticalLayout_13.addWidget(self.opts_resolution)

        self.opts_monitor = QGroupBox(self.scrollAreaWidgetContents_2)
        self.opts_monitor.setObjectName(u"opts_monitor")
        self.opts_monitor.setCheckable(True)
        self.opts_monitor.setChecked(False)
        self.verticalLayout_7 = QVBoxLayout(self.opts_monitor)
        self.verticalLayout_7.setObjectName(u"verticalLayout_7")
        self.label_26 = QLabel(self.opts_monitor)
        self.label_26.setObjectName(u"label_26")
        self.label_26.setWordWrap(True)

        self.verticalLayout_7.addWidget(self.label_26)

        self.label_27 = QLabel(self.opts_monitor)
        self.label_27.setObjectName(u"label_27")
        self.label_27.setWordWrap(True)

        self.verticalLayout_7.addWidget(self.label_27)

        self.multi_monitor = QRadioButton(self.opts_monitor)
        self.multi_monitor.setObjectName(u"multi_monitor")
        self.multi_monitor.setChecked(True)

        self.verticalLayout_7.addWidget(self.multi_monitor)

        self.single_monitor = QRadioButton(self.opts_monitor)
        self.single_monitor.setObjectName(u"single_monitor")

        self.verticalLayout_7.addWidget(self.single_monitor)


        self.verticalLayout_13.addWidget(self.opts_monitor)

        self.opts_tracking = QGroupBox(self.scrollAreaWidgetContents_2)
        self.opts_tracking.setObjectName(u"opts_tracking")
        self.verticalLayout_11 = QVBoxLayout(self.opts_tracking)
        self.verticalLayout_11.setObjectName(u"verticalLayout_11")
        self.label_25 = QLabel(self.opts_tracking)
        self.label_25.setObjectName(u"label_25")
        self.label_25.setWordWrap(True)

        self.verticalLayout_11.addWidget(self.label_25)

        self.gridLayout_2 = QGridLayout()
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.track_mouse = QCheckBox(self.opts_tracking)
        self.track_mouse.setObjectName(u"track_mouse")
        self.track_mouse.setChecked(True)

        self.gridLayout_2.addWidget(self.track_mouse, 0, 0, 1, 1)

        self.delete_mouse = QPushButton(self.opts_tracking)
        self.delete_mouse.setObjectName(u"delete_mouse")

        self.gridLayout_2.addWidget(self.delete_mouse, 0, 1, 1, 1)

        self.track_keyboard = QCheckBox(self.opts_tracking)
        self.track_keyboard.setObjectName(u"track_keyboard")
        self.track_keyboard.setChecked(True)

        self.gridLayout_2.addWidget(self.track_keyboard, 1, 0, 1, 1)

        self.delete_keyboard = QPushButton(self.opts_tracking)
        self.delete_keyboard.setObjectName(u"delete_keyboard")

        self.gridLayout_2.addWidget(self.delete_keyboard, 1, 1, 1, 1)

        self.track_gamepad = QCheckBox(self.opts_tracking)
        self.track_gamepad.setObjectName(u"track_gamepad")
        self.track_gamepad.setChecked(True)

        self.gridLayout_2.addWidget(self.track_gamepad, 2, 0, 1, 1)

        self.delete_gamepad = QPushButton(self.opts_tracking)
        self.delete_gamepad.setObjectName(u"delete_gamepad")

        self.gridLayout_2.addWidget(self.delete_gamepad, 2, 1, 1, 1)

        self.track_network = QCheckBox(self.opts_tracking)
        self.track_network.setObjectName(u"track_network")
        self.track_network.setChecked(True)

        self.gridLayout_2.addWidget(self.track_network, 3, 0, 1, 1)

        self.delete_network = QPushButton(self.opts_tracking)
        self.delete_network.setObjectName(u"delete_network")

        self.gridLayout_2.addWidget(self.delete_network, 3, 1, 1, 1)


        self.verticalLayout_11.addLayout(self.gridLayout_2)

        self.delete_profile = QPushButton(self.opts_tracking)
        self.delete_profile.setObjectName(u"delete_profile")

        self.verticalLayout_11.addWidget(self.delete_profile)


        self.verticalLayout_13.addWidget(self.opts_tracking)

        self.verticalSpacer_4 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_13.addItem(self.verticalSpacer_4)

        self.scrollArea_2.setWidget(self.scrollAreaWidgetContents_2)

        self.verticalLayout_15.addWidget(self.scrollArea_2)

        self.tab_options.addTab(self.tab_profile_options, "")
        self.tab_4 = QWidget()
        self.tab_4.setObjectName(u"tab_4")
        self.verticalLayout_10 = QVBoxLayout(self.tab_4)
        self.verticalLayout_10.setObjectName(u"verticalLayout_10")
        self.scrollArea_3 = QScrollArea(self.tab_4)
        self.scrollArea_3.setObjectName(u"scrollArea_3")
        self.scrollArea_3.setWidgetResizable(True)
        self.scrollAreaWidgetContents_3 = QWidget()
        self.scrollAreaWidgetContents_3.setObjectName(u"scrollAreaWidgetContents_3")
        self.scrollAreaWidgetContents_3.setGeometry(QRect(0, 0, 311, 486))
        self.verticalLayout = QVBoxLayout(self.scrollAreaWidgetContents_3)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.groupBox_11 = QGroupBox(self.scrollAreaWidgetContents_3)
        self.groupBox_11.setObjectName(u"groupBox_11")
        self.verticalLayout_8 = QVBoxLayout(self.groupBox_11)
        self.verticalLayout_8.setObjectName(u"verticalLayout_8")
        self.gridLayout_5 = QGridLayout()
        self.gridLayout_5.setObjectName(u"gridLayout_5")
        self.stat_app_title = QLabel(self.groupBox_11)
        self.stat_app_title.setObjectName(u"stat_app_title")
        self.stat_app_title.setWordWrap(True)

        self.gridLayout_5.addWidget(self.stat_app_title, 1, 1, 1, 1)

        self.stat_app_exe = QLabel(self.groupBox_11)
        self.stat_app_exe.setObjectName(u"stat_app_exe")
        self.stat_app_exe.setWordWrap(True)

        self.gridLayout_5.addWidget(self.stat_app_exe, 0, 1, 1, 1)

        self.label_10 = QLabel(self.groupBox_11)
        self.label_10.setObjectName(u"label_10")

        self.gridLayout_5.addWidget(self.label_10, 1, 0, 1, 1)

        self.label_5 = QLabel(self.groupBox_11)
        self.label_5.setObjectName(u"label_5")

        self.gridLayout_5.addWidget(self.label_5, 0, 0, 1, 1)

        self.label_6 = QLabel(self.groupBox_11)
        self.label_6.setObjectName(u"label_6")

        self.gridLayout_5.addWidget(self.label_6, 2, 0, 1, 1)

        self.stat_app_tracked = QLabel(self.groupBox_11)
        self.stat_app_tracked.setObjectName(u"stat_app_tracked")

        self.gridLayout_5.addWidget(self.stat_app_tracked, 2, 1, 1, 1)


        self.verticalLayout_8.addLayout(self.gridLayout_5)

        self.stat_app_add = QPushButton(self.groupBox_11)
        self.stat_app_add.setObjectName(u"stat_app_add")

        self.verticalLayout_8.addWidget(self.stat_app_add)


        self.verticalLayout.addWidget(self.groupBox_11)

        self.groupBox_10 = QGroupBox(self.scrollAreaWidgetContents_3)
        self.groupBox_10.setObjectName(u"groupBox_10")
        self.gridLayout_4 = QGridLayout(self.groupBox_10)
        self.gridLayout_4.setObjectName(u"gridLayout_4")
        self.time_since_thumbnail = QLabel(self.groupBox_10)
        self.time_since_thumbnail.setObjectName(u"time_since_thumbnail")

        self.gridLayout_4.addWidget(self.time_since_thumbnail, 1, 1, 1, 1)

        self.save = QPushButton(self.groupBox_10)
        self.save.setObjectName(u"save")

        self.gridLayout_4.addWidget(self.save, 0, 0, 1, 1)

        self.thumbnail_refresh = QPushButton(self.groupBox_10)
        self.thumbnail_refresh.setObjectName(u"thumbnail_refresh")

        self.gridLayout_4.addWidget(self.thumbnail_refresh, 1, 0, 1, 1)

        self.horizontalLayout_7 = QHBoxLayout()
        self.horizontalLayout_7.setObjectName(u"horizontalLayout_7")
        self.time_since_save = QLabel(self.groupBox_10)
        self.time_since_save.setObjectName(u"time_since_save")

        self.horizontalLayout_7.addWidget(self.time_since_save)

        self.autosave = QCheckBox(self.groupBox_10)
        self.autosave.setObjectName(u"autosave")
        self.autosave.setChecked(True)

        self.horizontalLayout_7.addWidget(self.autosave)


        self.gridLayout_4.addLayout(self.horizontalLayout_7, 0, 1, 1, 1)

        self.time_since_applist_reload = QLabel(self.groupBox_10)
        self.time_since_applist_reload.setObjectName(u"time_since_applist_reload")

        self.gridLayout_4.addWidget(self.time_since_applist_reload, 2, 1, 1, 1)

        self.applist_reload = QPushButton(self.groupBox_10)
        self.applist_reload.setObjectName(u"applist_reload")

        self.gridLayout_4.addWidget(self.applist_reload, 2, 0, 1, 1)


        self.verticalLayout.addWidget(self.groupBox_10)

        self.status_components = QGroupBox(self.scrollAreaWidgetContents_3)
        self.status_components.setObjectName(u"status_components")
        self.gridLayout_8 = QGridLayout(self.status_components)
        self.gridLayout_8.setObjectName(u"gridLayout_8")
        self.status_hub_state = QLabel(self.status_components)
        self.status_hub_state.setObjectName(u"status_hub_state")

        self.gridLayout_8.addWidget(self.status_hub_state, 1, 2, 1, 1)

        self.status_app_state = QLabel(self.status_components)
        self.status_app_state.setObjectName(u"status_app_state")

        self.gridLayout_8.addWidget(self.status_app_state, 5, 2, 1, 1)

        self.status_hub_pid = QLabel(self.status_components)
        self.status_hub_pid.setObjectName(u"status_hub_pid")

        self.gridLayout_8.addWidget(self.status_hub_pid, 1, 1, 1, 1)

        self.status_tracking_state = QLabel(self.status_components)
        self.status_tracking_state.setObjectName(u"status_tracking_state")

        self.gridLayout_8.addWidget(self.status_tracking_state, 2, 2, 1, 1)

        self.status_header_name = QLabel(self.status_components)
        self.status_header_name.setObjectName(u"status_header_name")
        self.status_header_name.setTextFormat(Qt.TextFormat.MarkdownText)

        self.gridLayout_8.addWidget(self.status_header_name, 0, 0, 1, 1)

        self.status_gui_name = QLabel(self.status_components)
        self.status_gui_name.setObjectName(u"status_gui_name")

        self.gridLayout_8.addWidget(self.status_gui_name, 4, 0, 1, 1)

        self.status_processing_pid = QLabel(self.status_components)
        self.status_processing_pid.setObjectName(u"status_processing_pid")

        self.gridLayout_8.addWidget(self.status_processing_pid, 3, 1, 1, 1)

        self.status_header_state = QLabel(self.status_components)
        self.status_header_state.setObjectName(u"status_header_state")
        self.status_header_state.setTextFormat(Qt.TextFormat.MarkdownText)

        self.gridLayout_8.addWidget(self.status_header_state, 0, 2, 1, 1)

        self.status_app_pid = QLabel(self.status_components)
        self.status_app_pid.setObjectName(u"status_app_pid")

        self.gridLayout_8.addWidget(self.status_app_pid, 5, 1, 1, 1)

        self.status_hub_name = QLabel(self.status_components)
        self.status_hub_name.setObjectName(u"status_hub_name")

        self.gridLayout_8.addWidget(self.status_hub_name, 1, 0, 1, 1)

        self.status_header_pid = QLabel(self.status_components)
        self.status_header_pid.setObjectName(u"status_header_pid")
        self.status_header_pid.setTextFormat(Qt.TextFormat.MarkdownText)

        self.gridLayout_8.addWidget(self.status_header_pid, 0, 1, 1, 1)

        self.status_app_name = QLabel(self.status_components)
        self.status_app_name.setObjectName(u"status_app_name")

        self.gridLayout_8.addWidget(self.status_app_name, 5, 0, 1, 1)

        self.status_tracking_name = QLabel(self.status_components)
        self.status_tracking_name.setObjectName(u"status_tracking_name")

        self.gridLayout_8.addWidget(self.status_tracking_name, 2, 0, 1, 1)

        self.status_processing_state = QLabel(self.status_components)
        self.status_processing_state.setObjectName(u"status_processing_state")

        self.gridLayout_8.addWidget(self.status_processing_state, 3, 2, 1, 1)

        self.status_gui_state = QLabel(self.status_components)
        self.status_gui_state.setObjectName(u"status_gui_state")

        self.gridLayout_8.addWidget(self.status_gui_state, 4, 2, 1, 1)

        self.status_processing_name = QLabel(self.status_components)
        self.status_processing_name.setObjectName(u"status_processing_name")

        self.gridLayout_8.addWidget(self.status_processing_name, 3, 0, 1, 1)

        self.status_tracking_pid = QLabel(self.status_components)
        self.status_tracking_pid.setObjectName(u"status_tracking_pid")

        self.gridLayout_8.addWidget(self.status_tracking_pid, 2, 1, 1, 1)

        self.status_gui_pid = QLabel(self.status_components)
        self.status_gui_pid.setObjectName(u"status_gui_pid")

        self.gridLayout_8.addWidget(self.status_gui_pid, 4, 1, 1, 1)

        self.status_header_queue = QLabel(self.status_components)
        self.status_header_queue.setObjectName(u"status_header_queue")
        sizePolicy1.setHeightForWidth(self.status_header_queue.sizePolicy().hasHeightForWidth())
        self.status_header_queue.setSizePolicy(sizePolicy1)
        self.status_header_queue.setTextFormat(Qt.TextFormat.MarkdownText)

        self.gridLayout_8.addWidget(self.status_header_queue, 0, 3, 1, 1)

        self.status_hub_queue = QLabel(self.status_components)
        self.status_hub_queue.setObjectName(u"status_hub_queue")

        self.gridLayout_8.addWidget(self.status_hub_queue, 1, 3, 1, 1)

        self.status_tracking_queue = QLabel(self.status_components)
        self.status_tracking_queue.setObjectName(u"status_tracking_queue")

        self.gridLayout_8.addWidget(self.status_tracking_queue, 2, 3, 1, 1)

        self.status_processing_queue = QLabel(self.status_components)
        self.status_processing_queue.setObjectName(u"status_processing_queue")

        self.gridLayout_8.addWidget(self.status_processing_queue, 3, 3, 1, 1)

        self.status_gui_queue = QLabel(self.status_components)
        self.status_gui_queue.setObjectName(u"status_gui_queue")

        self.gridLayout_8.addWidget(self.status_gui_queue, 4, 3, 1, 1)

        self.status_app_queue = QLabel(self.status_components)
        self.status_app_queue.setObjectName(u"status_app_queue")

        self.gridLayout_8.addWidget(self.status_app_queue, 5, 3, 1, 1)


        self.verticalLayout.addWidget(self.status_components)

        self.verticalSpacer_2 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout.addItem(self.verticalSpacer_2)

        self.scrollArea_3.setWidget(self.scrollAreaWidgetContents_3)

        self.verticalLayout_10.addWidget(self.scrollArea_3)

        self.tab_options.addTab(self.tab_4, "")
        self.horizontal_splitter.addWidget(self.tab_options)
        self.vertical_splitter.addWidget(self.horizontal_splitter)
        self.output_logs = QTabWidget(self.vertical_splitter)
        self.output_logs.setObjectName(u"output_logs")
        self.output_logs.setEnabled(False)
        self.tab_6 = QWidget()
        self.tab_6.setObjectName(u"tab_6")
        self.verticalLayout_5 = QVBoxLayout(self.tab_6)
        self.verticalLayout_5.setObjectName(u"verticalLayout_5")
        self.listWidget_3 = QListWidget(self.tab_6)
        QListWidgetItem(self.listWidget_3)
        QListWidgetItem(self.listWidget_3)
        QListWidgetItem(self.listWidget_3)
        QListWidgetItem(self.listWidget_3)
        QListWidgetItem(self.listWidget_3)
        QListWidgetItem(self.listWidget_3)
        QListWidgetItem(self.listWidget_3)
        QListWidgetItem(self.listWidget_3)
        QListWidgetItem(self.listWidget_3)
        QListWidgetItem(self.listWidget_3)
        QListWidgetItem(self.listWidget_3)
        QListWidgetItem(self.listWidget_3)
        QListWidgetItem(self.listWidget_3)
        QListWidgetItem(self.listWidget_3)
        QListWidgetItem(self.listWidget_3)
        QListWidgetItem(self.listWidget_3)
        QListWidgetItem(self.listWidget_3)
        QListWidgetItem(self.listWidget_3)
        QListWidgetItem(self.listWidget_3)
        self.listWidget_3.setObjectName(u"listWidget_3")
        self.listWidget_3.setMinimumSize(QSize(0, 0))

        self.verticalLayout_5.addWidget(self.listWidget_3)

        self.output_logs.addTab(self.tab_6, "")
        self.tab_7 = QWidget()
        self.tab_7.setObjectName(u"tab_7")
        self.output_logs.addTab(self.tab_7, "")
        self.vertical_splitter.addWidget(self.output_logs)

        self.main_layout.addWidget(self.vertical_splitter)

        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QMenuBar(MainWindow)
        self.menubar.setObjectName(u"menubar")
        self.menubar.setGeometry(QRect(0, 0, 1060, 22))
        self.menuFile = QMenu(self.menubar)
        self.menuFile.setObjectName(u"menuFile")
        self.menuExport = QMenu(self.menuFile)
        self.menuExport.setObjectName(u"menuExport")
        self.menuHelp = QMenu(self.menubar)
        self.menuHelp.setObjectName(u"menuHelp")
        self.menuPreferences = QMenu(self.menubar)
        self.menuPreferences.setObjectName(u"menuPreferences")
        self.menuStartup = QMenu(self.menuPreferences)
        self.menuStartup.setObjectName(u"menuStartup")
        self.tray_context_menu = QMenu(self.menubar)
        self.tray_context_menu.setObjectName(u"tray_context_menu")
        self.menu_debug = QMenu(self.tray_context_menu)
        self.menu_debug.setObjectName(u"menu_debug")
        self.menu_debug_state = QMenu(self.menu_debug)
        self.menu_debug_state.setObjectName(u"menu_debug_state")
        self.menu_debug_raise = QMenu(self.menu_debug)
        self.menu_debug_raise.setObjectName(u"menu_debug_raise")
        self.menuTracking = QMenu(self.menubar)
        self.menuTracking.setObjectName(u"menuTracking")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QStatusBar(MainWindow)
        self.statusbar.setObjectName(u"statusbar")
        MainWindow.setStatusBar(self.statusbar)
#if QT_CONFIG(shortcut)
        self.custom_height_label.setBuddy(self.custom_height)
        self.custom_width_label.setBuddy(self.custom_width)
        self.sampling_label.setBuddy(self.sampling)
        self.label_14.setBuddy(self.clipping)
        self.label_16.setBuddy(self.padding)
        self.label_18.setBuddy(self.blur)
        self.label_31.setBuddy(self.interpolation_order)
        self.contrast_label.setBuddy(self.contrast)
        self.label_28.setBuddy(self.thumbnail_sampling)
        self.label_24.setBuddy(self.colour_option)
        self.label_33.setBuddy(self.layer_blending)
        self.label_32.setBuddy(self.layer_opacity)
#endif // QT_CONFIG(shortcut)

        self.menubar.addAction(self.menuFile.menuAction())
        self.menubar.addAction(self.menuPreferences.menuAction())
        self.menubar.addAction(self.menuTracking.menuAction())
        self.menubar.addAction(self.menuHelp.menuAction())
        self.menubar.addAction(self.tray_context_menu.menuAction())
        self.menuFile.addAction(self.file_tracking_start)
        self.menuFile.addAction(self.file_tracking_pause)
        self.menuFile.addSeparator()
        self.menuFile.addAction(self.file_save)
        self.menuFile.addAction(self.file_import)
        self.menuFile.addAction(self.menuExport.menuAction())
        self.menuFile.addSeparator()
        self.menuFile.addAction(self.menu_exit)
        self.menuExport.addAction(self.export_mouse_stats)
        self.menuExport.addAction(self.export_keyboard_stats)
        self.menuExport.addAction(self.export_network_stats)
        self.menuExport.addAction(self.export_gamepad_stats)
        self.menuExport.addAction(self.export_daily_stats)
        self.menuHelp.addAction(self.link_github)
        self.menuHelp.addAction(self.link_reddit)
        self.menuHelp.addAction(self.link_facebook)
        self.menuHelp.addSeparator()
        self.menuHelp.addAction(self.link_donate)
        self.menuHelp.addSeparator()
        self.menuHelp.addAction(self.about)
        self.menuPreferences.addAction(self.menuStartup.menuAction())
        self.menuPreferences.addSeparator()
        self.menuPreferences.addAction(self.prefs_console)
        self.menuPreferences.addAction(self.menu_allow_minimise)
        self.menuPreferences.addSeparator()
        self.menuPreferences.addAction(self.always_on_top)
        self.menuPreferences.addAction(self.full_screen)
        self.menuStartup.addAction(self.prefs_autostart)
        self.menuStartup.addAction(self.prefs_automin)
        self.tray_context_menu.addAction(self.tray_show)
        self.tray_context_menu.addAction(self.tray_hide)
        self.tray_context_menu.addSeparator()
        self.tray_context_menu.addAction(self.tray_app_add)
        self.tray_context_menu.addSeparator()
        self.tray_context_menu.addAction(self.tray_donate)
        self.tray_context_menu.addSeparator()
        self.tray_context_menu.addAction(self.menu_debug.menuAction())
        self.tray_context_menu.addAction(self.tray_about)
        self.tray_context_menu.addSeparator()
        self.tray_context_menu.addAction(self.tray_exit)
        self.menu_debug.addAction(self.menu_debug_state.menuAction())
        self.menu_debug.addAction(self.menu_debug_raise.menuAction())
        self.menu_debug.addAction(self.debug_pause_app)
        self.menu_debug.addAction(self.debug_pause_monitor)
        self.menu_debug_state.addAction(self.debug_state_running)
        self.menu_debug_state.addAction(self.debug_state_paused)
        self.menu_debug_state.addAction(self.debug_state_stopped)
        self.menu_debug_raise.addAction(self.debug_raise_hub)
        self.menu_debug_raise.addAction(self.debug_raise_tracking)
        self.menu_debug_raise.addAction(self.debug_raise_processing)
        self.menu_debug_raise.addAction(self.debug_raise_gui)
        self.menu_debug_raise.addAction(self.debug_raise_app)
        self.menuTracking.addAction(self.prefs_track_mouse)
        self.menuTracking.addAction(self.prefs_track_keyboard)
        self.menuTracking.addAction(self.prefs_track_gamepad)
        self.menuTracking.addAction(self.prefs_track_network)

        self.retranslateUi(MainWindow)
        self.tray_about.triggered.connect(self.about.trigger)
        self.tray_donate.triggered.connect(self.link_donate.trigger)
        self.save.clicked.connect(self.file_save.trigger)
        self.enable_custom_width.toggled.connect(self.custom_width.setEnabled)
        self.enable_custom_height.toggled.connect(self.custom_height.setEnabled)
        self.tray_app_add.triggered.connect(self.stat_app_add.click)

        self.tab_options.setCurrentIndex(0)
        self.layer_list.setCurrentRow(1)
        self.output_logs.setCurrentIndex(1)


        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"MouseTracks", None))
        self.file_save.setText(QCoreApplication.translate("MainWindow", u"Save", None))
#if QT_CONFIG(shortcut)
        self.file_save.setShortcut(QCoreApplication.translate("MainWindow", u"Ctrl+S", None))
#endif // QT_CONFIG(shortcut)
        self.file_import.setText(QCoreApplication.translate("MainWindow", u"Import", None))
        self.menu_exit.setText(QCoreApplication.translate("MainWindow", u"Exit", None))
        self.menu_allow_minimise.setText(QCoreApplication.translate("MainWindow", u"Minimise to Tray", None))
        self.file_tracking_start.setText(QCoreApplication.translate("MainWindow", u"Start", None))
        self.file_tracking_pause.setText(QCoreApplication.translate("MainWindow", u"Pause", None))
        self.link_github.setText(QCoreApplication.translate("MainWindow", u"Github", None))
#if QT_CONFIG(tooltip)
        self.link_github.setToolTip(QCoreApplication.translate("MainWindow", u"Navigate to the Github repository.", None))
#endif // QT_CONFIG(tooltip)
        self.link_reddit.setText(QCoreApplication.translate("MainWindow", u"Reddit", None))
#if QT_CONFIG(tooltip)
        self.link_reddit.setToolTip(QCoreApplication.translate("MainWindow", u"Navigate to the r/MouseTracks subreddit.", None))
#endif // QT_CONFIG(tooltip)
        self.link_facebook.setText(QCoreApplication.translate("MainWindow", u"Facebook", None))
#if QT_CONFIG(tooltip)
        self.link_facebook.setToolTip(QCoreApplication.translate("MainWindow", u"Navigate to the Facebook page.", None))
#endif // QT_CONFIG(tooltip)
        self.tray_exit.setText(QCoreApplication.translate("MainWindow", u"Exit", None))
        self.tray_show.setText(QCoreApplication.translate("MainWindow", u"Open", None))
        self.tray_hide.setText(QCoreApplication.translate("MainWindow", u"Minimise to Tray", None))
        self.prefs_track_keyboard.setText(QCoreApplication.translate("MainWindow", u"Track Keyboard", None))
        self.prefs_track_gamepad.setText(QCoreApplication.translate("MainWindow", u"Track Gamepad", None))
        self.prefs_track_mouse.setText(QCoreApplication.translate("MainWindow", u"Track Mouse", None))
        self.prefs_autostart.setText(QCoreApplication.translate("MainWindow", u"Start MouseTracks at Login", None))
        self.prefs_automin.setText(QCoreApplication.translate("MainWindow", u"Minimise at Launch", None))
        self.prefs_console.setText(QCoreApplication.translate("MainWindow", u"Show Console", None))
        self.full_screen.setText(QCoreApplication.translate("MainWindow", u"Full Screen", None))
#if QT_CONFIG(shortcut)
        self.full_screen.setShortcut(QCoreApplication.translate("MainWindow", u"F11", None))
#endif // QT_CONFIG(shortcut)
        self.prefs_track_network.setText(QCoreApplication.translate("MainWindow", u"Track Network", None))
        self.always_on_top.setText(QCoreApplication.translate("MainWindow", u"Always on Top", None))
        self.debug_raise_hub.setText(QCoreApplication.translate("MainWindow", u"Hub", None))
        self.debug_state_running.setText(QCoreApplication.translate("MainWindow", u"Running", None))
        self.debug_state_paused.setText(QCoreApplication.translate("MainWindow", u"Paused", None))
        self.debug_state_stopped.setText(QCoreApplication.translate("MainWindow", u"Stopped", None))
        self.debug_raise_tracking.setText(QCoreApplication.translate("MainWindow", u"Tracking", None))
        self.debug_raise_processing.setText(QCoreApplication.translate("MainWindow", u"Processing", None))
        self.debug_raise_gui.setText(QCoreApplication.translate("MainWindow", u"GUI", None))
        self.debug_raise_app.setText(QCoreApplication.translate("MainWindow", u"Application Detection", None))
        self.export_mouse_stats.setText(QCoreApplication.translate("MainWindow", u"Mouse Stats", None))
        self.export_keyboard_stats.setText(QCoreApplication.translate("MainWindow", u"Keyboard Stats", None))
        self.export_network_stats.setText(QCoreApplication.translate("MainWindow", u"Network Stats", None))
        self.export_gamepad_stats.setText(QCoreApplication.translate("MainWindow", u"Gamepad Stats", None))
        self.export_daily_stats.setText(QCoreApplication.translate("MainWindow", u"Daily Stats", None))
        self.about.setText(QCoreApplication.translate("MainWindow", u"About", None))
        self.tray_about.setText(QCoreApplication.translate("MainWindow", u"About", None))
        self.tray_app_add.setText(QCoreApplication.translate("MainWindow", u"Add Tracked Application", None))
        self.tray_donate.setText(QCoreApplication.translate("MainWindow", u"Donate", None))
        self.link_donate.setText(QCoreApplication.translate("MainWindow", u"Donate", None))
        self.debug_pause_app.setText(QCoreApplication.translate("MainWindow", u"Pause Application Detection", None))
        self.debug_pause_monitor.setText(QCoreApplication.translate("MainWindow", u"Pause Monitor Check", None))
#if QT_CONFIG(tooltip)
        self.thumbnail.setToolTip(QCoreApplication.translate("MainWindow", u"Live preview of the render.\n"
"\n"
"Click to pause or resume the tracking.\n"
"\n"
"Note that the full quality render will look slightly different due to\n"
"how the downscaling works, as each line needs to be made thicker to\n"
"combat aliasing.", None))
#endif // QT_CONFIG(tooltip)
        self.thumbnail.setText(QCoreApplication.translate("MainWindow", u"<image>", None))
        self.groupBox_2.setTitle(QCoreApplication.translate("MainWindow", u"Profile Selection", None))
        self.current_profile.setItemText(0, QCoreApplication.translate("MainWindow", u"*Main", None))
        self.current_profile.setItemText(1, QCoreApplication.translate("MainWindow", u"*Path of Exile", None))
        self.current_profile.setItemText(2, QCoreApplication.translate("MainWindow", u"Overwatch", None))

#if QT_CONFIG(tooltip)
        self.current_profile.setToolTip(QCoreApplication.translate("MainWindow", u"Select which profile to show.\n"
"An asterisk indicates that a profile has unsaved changes and will be saved.\n"
"Changing this does not affect what profile is currently being tracked.", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(tooltip)
        self.auto_switch_profile.setToolTip(QCoreApplication.translate("MainWindow", u"Keep the currently loaded profile selected.\n"
"When a new profile is recorded to, the GUI will immediately update.", None))
#endif // QT_CONFIG(tooltip)
        self.auto_switch_profile.setText(QCoreApplication.translate("MainWindow", u"Keep currently loaded selected", None))
        self.resolution_group.setTitle(QCoreApplication.translate("MainWindow", u"Resolution", None))
#if QT_CONFIG(tooltip)
        self.custom_height_label.setToolTip(QCoreApplication.translate("MainWindow", u"!inherit custom_height", None))
#endif // QT_CONFIG(tooltip)
        self.custom_height_label.setText(QCoreApplication.translate("MainWindow", u"Height Override:", None))
#if QT_CONFIG(tooltip)
        self.lock_aspect.setToolTip(QCoreApplication.translate("MainWindow", u"Set if the aspect ratio should be locked to the recommended value.", None))
#endif // QT_CONFIG(tooltip)
        self.lock_aspect.setText(QCoreApplication.translate("MainWindow", u"Lock Aspect Ratio", None))
#if QT_CONFIG(tooltip)
        self.custom_height.setToolTip(QCoreApplication.translate("MainWindow", u"Set an override to render at a specific height.\n"
"\n"
"If the aspect ratio is locked and a width override is set,\n"
"then the render may end up smaller than this override.", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(tooltip)
        self.enable_custom_height.setToolTip(QCoreApplication.translate("MainWindow", u"Enable the height override.\n"
"If this is disabled, the height will be set based on the available data.", None))
#endif // QT_CONFIG(tooltip)
        self.enable_custom_height.setText("")
#if QT_CONFIG(tooltip)
        self.custom_width.setToolTip(QCoreApplication.translate("MainWindow", u"Set an override to render at a specific width.\n"
"\n"
"If the aspect ratio is locked and a height override is set,\n"
"then the render may end up smaller than this override.", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(tooltip)
        self.enable_custom_width.setToolTip(QCoreApplication.translate("MainWindow", u"Enable the width override.\n"
"If this is disabled, the width will be set based on the available data.", None))
#endif // QT_CONFIG(tooltip)
        self.enable_custom_width.setText("")
#if QT_CONFIG(tooltip)
        self.custom_width_label.setToolTip(QCoreApplication.translate("MainWindow", u"!inherit custom_width", None))
#endif // QT_CONFIG(tooltip)
        self.custom_width_label.setText(QCoreApplication.translate("MainWindow", u"Width Override:", None))
        self.groupBox_3.setTitle(QCoreApplication.translate("MainWindow", u"Data Type", None))
#if QT_CONFIG(tooltip)
        self.show_left_clicks.setToolTip(QCoreApplication.translate("MainWindow", u"Show left mouse clicks / left thumbstick.", None))
#endif // QT_CONFIG(tooltip)
        self.show_left_clicks.setText(QCoreApplication.translate("MainWindow", u"Left", None))
#if QT_CONFIG(tooltip)
        self.show_middle_clicks.setToolTip(QCoreApplication.translate("MainWindow", u"Show middle mouse clicks.", None))
#endif // QT_CONFIG(tooltip)
        self.show_middle_clicks.setText(QCoreApplication.translate("MainWindow", u"Middle", None))
#if QT_CONFIG(tooltip)
        self.show_right_clicks.setToolTip(QCoreApplication.translate("MainWindow", u"Show right mouse clicks / right thumbstick.", None))
#endif // QT_CONFIG(tooltip)
        self.show_right_clicks.setText(QCoreApplication.translate("MainWindow", u"Right", None))
#if QT_CONFIG(tooltip)
        self.map_type.setToolTip(QCoreApplication.translate("MainWindow", u"Select which dataset to render.\n"
"If no data exists, then a blank image will be shown.", None))
#endif // QT_CONFIG(tooltip)
        self.show_count.setText(QCoreApplication.translate("MainWindow", u"Count", None))
        self.show_time.setText(QCoreApplication.translate("MainWindow", u"Time", None))
        self.groupBox_5.setTitle(QCoreApplication.translate("MainWindow", u"Render Settings", None))
#if QT_CONFIG(tooltip)
        self.thumbnail_sampling.setToolTip(QCoreApplication.translate("MainWindow", u"Set the level of sampling used for the preview render.\n"
"\n"
"The default behaviour is a sample level of 0, which is optimised for\n"
"low resolution previews, but is not representative of the final render.\n"
"\n"
"A sample level of 1 or higher will match the output render. Lower\n"
"sample levels will be aliased however, and higher sample levels\n"
"require more processing.", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(tooltip)
        self.contrast.setToolTip(QCoreApplication.translate("MainWindow", u"Set the contrast of the render.\n"
"\n"
"This applies an exponential adjustment to enhance or reduce colour variation.", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(tooltip)
        self.sampling_label.setToolTip(QCoreApplication.translate("MainWindow", u"!inherit sampling", None))
#endif // QT_CONFIG(tooltip)
        self.sampling_label.setText(QCoreApplication.translate("MainWindow", u"Sampling (Render):", None))
#if QT_CONFIG(tooltip)
        self.label_14.setToolTip(QCoreApplication.translate("MainWindow", u"!inherit clipping", None))
#endif // QT_CONFIG(tooltip)
        self.label_14.setText(QCoreApplication.translate("MainWindow", u"Clipping:", None))
#if QT_CONFIG(tooltip)
        self.label_16.setToolTip(QCoreApplication.translate("MainWindow", u"!inherit padding", None))
#endif // QT_CONFIG(tooltip)
        self.label_16.setText(QCoreApplication.translate("MainWindow", u"Padding:", None))
        self.colour_option.setItemText(0, QCoreApplication.translate("MainWindow", u"Default", None))
        self.colour_option.setItemText(1, QCoreApplication.translate("MainWindow", u"Citrus", None))
        self.colour_option.setItemText(2, QCoreApplication.translate("MainWindow", u"Sunburst", None))

#if QT_CONFIG(tooltip)
        self.colour_option.setToolTip(QCoreApplication.translate("MainWindow", u"<html><head/><body><p>Set the colour map for the render.<br/>The preset maps are shown, but custom maps can be input.</p><p><span style=\" font-weight:700;\">Colours<br/></span>Preset colour names or hex values can be used.<br/>Supported hex values are #RGB, #RGBA, #RRGGBB, #RRGGBBAA.</p><p><span style=\" font-weight:700;\">Groups<br/></span>A group of colours are mixed together to create the final colour.<br/>Combine multiple colours by writing them next to each other.<br/><span style=\" font-style:italic;\">eg. YellowPinkRed will result in a deep orange.</span></p><p><span style=\" font-weight:700;\">Transitions<br/></span>Separate groups with a &quot;To&quot; to create a transition between the two.<br/>eg. BlackTo<span style=\" font-style:italic;\">YellowPinkRed</span> will create a colour map from black to that deep orange.</p><p><span style=\" font-weight:700;\">Modifiers<br/></span>Used as prefixes to modify an individual colour.<br/><span style=\" font-style:italic;\">Supported: dark, light, transparent"
                        ", translucent, opaque<br/>eg. LightYellowOrange will combine orange with light yellow.</span></p><p><span style=\" font-weight:700;\">Duplicates<br/></span>Multiply the effect of the next word.<br/><span style=\" font-style:italic;\">Supported: single, double, triple, quadruple, ...<br/>eg. TripleDarkRed is red with the dark modifier applied 3 times</span></p><p><span style=\" font-weight:700;\">Examples<br/></span>The default <span style=\" font-style:italic;\">Ice</span> colour map is defined as <span style=\" font-style:italic;\">BlackToDarkBlueToDarkBlueLightDarkCyanToLightBlueDarkCyanToWhite</span>.<br/>The <span style=\" font-style:italic;\">Citrus</span> map is <span style=\" font-style:italic;\">BlackToDarkDarkGreyToDarkGreenToYellow</span>.</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(tooltip)
        self.sampling.setToolTip(QCoreApplication.translate("MainWindow", u"Set the render sampling level.\n"
"\n"
"Higher sampling improves accuracy when combining data from\n"
"different resolutions, especially for lower-resolution recordings.\n"
"\n"
"A value of 0 will turn off all upscaling, and will instead run the\n"
"resampling that's in use by the preview image, where lines will\n"
"get thicker at lower resolutions.", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(tooltip)
        self.label_18.setToolTip(QCoreApplication.translate("MainWindow", u"!inherit blur", None))
#endif // QT_CONFIG(tooltip)
        self.label_18.setText(QCoreApplication.translate("MainWindow", u"Blur:", None))
#if QT_CONFIG(tooltip)
        self.label_31.setToolTip(QCoreApplication.translate("MainWindow", u"!inherit interpolation_order", None))
#endif // QT_CONFIG(tooltip)
        self.label_31.setText(QCoreApplication.translate("MainWindow", u"Interpolation:", None))
#if QT_CONFIG(tooltip)
        self.contrast_label.setToolTip(QCoreApplication.translate("MainWindow", u"!inherit contrast", None))
#endif // QT_CONFIG(tooltip)
        self.contrast_label.setText(QCoreApplication.translate("MainWindow", u"Contrast:", None))
#if QT_CONFIG(tooltip)
        self.padding.setToolTip(QCoreApplication.translate("MainWindow", u"Adjust the padding around the render.\n"
"\n"
"Note that this may affect the intensity of heatmap edges.", None))
#endif // QT_CONFIG(tooltip)
        self.padding.setSuffix(QCoreApplication.translate("MainWindow", u"px", None))
#if QT_CONFIG(tooltip)
        self.linear.setToolTip(QCoreApplication.translate("MainWindow", u"Use a linear mapping of the data, ensuring a smooth colour range.", None))
#endif // QT_CONFIG(tooltip)
        self.linear.setText(QCoreApplication.translate("MainWindow", u"Linear Mapping", None))
#if QT_CONFIG(tooltip)
        self.interpolation_order.setToolTip(QCoreApplication.translate("MainWindow", u"Set the order of the spline interpolation to use when upscaling arrays.\n"
"Any values other than 0 will cause inaccurate colour mappings.\n"
"\n"
"Preview Sampling must be greater than 0 to see the changes.", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(tooltip)
        self.clipping.setToolTip(QCoreApplication.translate("MainWindow", u"Define a clipping threshold.\n"
"\n"
"Values in the highest percentage range will be clipped to\n"
"prevent overly bright spots from dominating the image.", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(tooltip)
        self.label_28.setToolTip(QCoreApplication.translate("MainWindow", u"!inherit thumbnail_sampling", None))
#endif // QT_CONFIG(tooltip)
        self.label_28.setText(QCoreApplication.translate("MainWindow", u"Sampling (Preview):", None))
#if QT_CONFIG(tooltip)
        self.blur.setToolTip(QCoreApplication.translate("MainWindow", u"Set the strength of the gaussian blur.\n"
"\n"
"This is primarily designed for use with heatmaps.", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(tooltip)
        self.label_24.setToolTip(QCoreApplication.translate("MainWindow", u"!inherit colour_option", None))
#endif // QT_CONFIG(tooltip)
        self.label_24.setText(QCoreApplication.translate("MainWindow", u"Colour Map:", None))
#if QT_CONFIG(tooltip)
        self.invert.setToolTip(QCoreApplication.translate("MainWindow", u"Invert the colour map.", None))
#endif // QT_CONFIG(tooltip)
        self.invert.setText(QCoreApplication.translate("MainWindow", u"Invert", None))
#if QT_CONFIG(tooltip)
        self.layer_group.setToolTip(QCoreApplication.translate("MainWindow", u"Use render layers to combine multiple renders together, making use of opacity and blending modes.\n"
"The \"Render Settings\" and \"Data Type\" options above are set per layer.", None))
#endif // QT_CONFIG(tooltip)
        self.layer_group.setTitle(QCoreApplication.translate("MainWindow", u"Render Layers", None))
        self.layer_presets.setItemText(0, QCoreApplication.translate("MainWindow", u"Presets", None))

#if QT_CONFIG(tooltip)
        self.layer_presets.setToolTip(QCoreApplication.translate("MainWindow", u"Choose a layer setup from a few defined presets.\n"
"This will overwrite your current setup.", None))
#endif // QT_CONFIG(tooltip)

        __sortingEnabled = self.layer_list.isSortingEnabled()
        self.layer_list.setSortingEnabled(False)
        ___qlistwidgetitem = self.layer_list.item(0)
        ___qlistwidgetitem.setText(QCoreApplication.translate("MainWindow", u"Layer 1", None));
        ___qlistwidgetitem1 = self.layer_list.item(1)
        ___qlistwidgetitem1.setText(QCoreApplication.translate("MainWindow", u"Layer 0", None));
        self.layer_list.setSortingEnabled(__sortingEnabled)

#if QT_CONFIG(tooltip)
        self.layer_list.setToolTip(QCoreApplication.translate("MainWindow", u"List of all the current layers, which can be reordered by dragging.\n"
"Use the checkbox to enable / disable layers.", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(tooltip)
        self.layer_add.setToolTip(QCoreApplication.translate("MainWindow", u"Add a new layer.\n"
"The new layer will be unchecked by default, so will not be initially shown.", None))
#endif // QT_CONFIG(tooltip)
        self.layer_add.setText(QCoreApplication.translate("MainWindow", u"+", None))
#if QT_CONFIG(tooltip)
        self.layer_remove.setToolTip(QCoreApplication.translate("MainWindow", u"Remove the selected layer.", None))
#endif // QT_CONFIG(tooltip)
        self.layer_remove.setText(QCoreApplication.translate("MainWindow", u"-", None))
#if QT_CONFIG(tooltip)
        self.layer_up.setToolTip(QCoreApplication.translate("MainWindow", u"Move the selected layer up.", None))
#endif // QT_CONFIG(tooltip)
        self.layer_up.setText(QCoreApplication.translate("MainWindow", u"\u2191", None))
#if QT_CONFIG(tooltip)
        self.layer_down.setToolTip(QCoreApplication.translate("MainWindow", u"Move the selected layer down.", None))
#endif // QT_CONFIG(tooltip)
        self.layer_down.setText(QCoreApplication.translate("MainWindow", u"\u2193", None))
#if QT_CONFIG(tooltip)
        self.label_33.setToolTip(QCoreApplication.translate("MainWindow", u"!inherit layer_blending", None))
#endif // QT_CONFIG(tooltip)
        self.label_33.setText(QCoreApplication.translate("MainWindow", u"Blending Mode:", None))
#if QT_CONFIG(tooltip)
        self.layer_r.setToolTip(QCoreApplication.translate("MainWindow", u"Enable the red channel for the current layer.", None))
#endif // QT_CONFIG(tooltip)
        self.layer_r.setText(QCoreApplication.translate("MainWindow", u"R", None))
#if QT_CONFIG(tooltip)
        self.layer_g.setToolTip(QCoreApplication.translate("MainWindow", u"Enable the green channel for the current layer.", None))
#endif // QT_CONFIG(tooltip)
        self.layer_g.setText(QCoreApplication.translate("MainWindow", u"G", None))
#if QT_CONFIG(tooltip)
        self.layer_b.setToolTip(QCoreApplication.translate("MainWindow", u"Enable the blue channel for the current layer.", None))
#endif // QT_CONFIG(tooltip)
        self.layer_b.setText(QCoreApplication.translate("MainWindow", u"B", None))
#if QT_CONFIG(tooltip)
        self.layer_a.setToolTip(QCoreApplication.translate("MainWindow", u"Enable the alpha channel for the current layer.", None))
#endif // QT_CONFIG(tooltip)
        self.layer_a.setText(QCoreApplication.translate("MainWindow", u"A", None))
#if QT_CONFIG(tooltip)
        self.layer_blending.setToolTip(QCoreApplication.translate("MainWindow", u"Set the blending mode of the current layer.", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(tooltip)
        self.layer_opacity.setToolTip(QCoreApplication.translate("MainWindow", u"Set the opacity of the selected layer.", None))
#endif // QT_CONFIG(tooltip)
        self.layer_opacity.setSuffix(QCoreApplication.translate("MainWindow", u"%", None))
#if QT_CONFIG(tooltip)
        self.label_34.setToolTip(QCoreApplication.translate("MainWindow", u"Set which channels to use from the current layer.\n"
"For example, it can be limited to Alpha to copy the transparency.", None))
#endif // QT_CONFIG(tooltip)
        self.label_34.setText(QCoreApplication.translate("MainWindow", u"Channels:", None))
#if QT_CONFIG(tooltip)
        self.label_32.setToolTip(QCoreApplication.translate("MainWindow", u"!inherit layer_opacity", None))
#endif // QT_CONFIG(tooltip)
        self.label_32.setText(QCoreApplication.translate("MainWindow", u"Opacity:", None))
        self.groupBox_9.setTitle(QCoreApplication.translate("MainWindow", u"Stats", None))
        self.label_9.setText(QCoreApplication.translate("MainWindow", u"Mouse Scrolls:", None))
        self.label_11.setText(QCoreApplication.translate("MainWindow", u"Elapsed Time:", None))
        self.stat_active.setText(QCoreApplication.translate("MainWindow", u"45.0 hours", None))
        self.label_8.setText(QCoreApplication.translate("MainWindow", u"Total Upload:", None))
        self.stat_clicks.setText(QCoreApplication.translate("MainWindow", u"526462", None))
        self.stat_scroll.setText(QCoreApplication.translate("MainWindow", u"316177", None))
        self.label_20.setText(QCoreApplication.translate("MainWindow", u"Keys Pressed:", None))
        self.label_22.setText(QCoreApplication.translate("MainWindow", u"Active Time:", None))
        self.stat_elapsed.setText(QCoreApplication.translate("MainWindow", u"50.30 hours", None))
        self.label_21.setText(QCoreApplication.translate("MainWindow", u"Mouse Clicks:", None))
        self.stat_keys.setText(QCoreApplication.translate("MainWindow", u"42544", None))
        self.stat_upload_total.setText(QCoreApplication.translate("MainWindow", u"643.16 MB", None))
        self.stat_inactive.setText(QCoreApplication.translate("MainWindow", u"5.30 hours", None))
        self.stat_download_total.setText(QCoreApplication.translate("MainWindow", u"1.32 TB", None))
        self.stat_buttons.setText(QCoreApplication.translate("MainWindow", u"264", None))
        self.label_19.setText(QCoreApplication.translate("MainWindow", u"Cursor Distance:", None))
        self.stat_distance.setText(QCoreApplication.translate("MainWindow", u"32.54km", None))
        self.label_4.setText(QCoreApplication.translate("MainWindow", u"Total Download:", None))
        self.label_29.setText(QCoreApplication.translate("MainWindow", u"Current Download:", None))
        self.label_23.setText(QCoreApplication.translate("MainWindow", u"Inactive Time:", None))
        self.label.setText(QCoreApplication.translate("MainWindow", u"Buttons Pressed:", None))
        self.label_30.setText(QCoreApplication.translate("MainWindow", u"Current Upload:", None))
        self.stat_download_current.setText(QCoreApplication.translate("MainWindow", u"3.5 Mb/s (0.3 MB/s)", None))
        self.stat_upload_current.setText(QCoreApplication.translate("MainWindow", u"80 Mb/s (8.2 MB/s)", None))
        self.record_history.setTitle(QCoreApplication.translate("MainWindow", u"History", None))
        self.label_7.setText(QCoreApplication.translate("MainWindow", u"Number of hours to keep available", None))
        self.tip.setText(QCoreApplication.translate("MainWindow", u"Tip: Not tracking your new game? Create a rule by clicking <strong>Add Tracked Application</strong> in the <strong>Status</strong> tab.", None))
        self.tip.setProperty(u"tip_tracking", QCoreApplication.translate("MainWindow", u"Not tracking your new game? Create a rule by clicking <strong>Add Tracked Application</strong> in the <strong>Status</strong> tab.", None))
        self.tip.setProperty(u"tip_update", QCoreApplication.translate("MainWindow", u"A new update is available. <a href=\"https://github.com/huntfx/MouseTracks/releases/latest\">Click here</a> to visit the download page.", None))
        self.tip.setProperty(u"tip_tooltip", QCoreApplication.translate("MainWindow", u"Don't understand an option? Hover over to show its tooltip, or <a href=\"https://github.com/huntfx/MouseTracks/issues\">raise an issue</a> if it needs improvement.", None))
        self.tip.setProperty(u"tip_install", QCoreApplication.translate("MainWindow", u"A new version is ready to install. Restart MouseTracks to complete the installation.", None))
#if QT_CONFIG(tooltip)
        self.save_render.setToolTip(QCoreApplication.translate("MainWindow", u"Save a full quality render to disk.\n"
"This may take a few seconds to complete.", None))
#endif // QT_CONFIG(tooltip)
        self.save_render.setText(QCoreApplication.translate("MainWindow", u"Save Render", None))
#if QT_CONFIG(tooltip)
        self.show_advanced.setToolTip(QCoreApplication.translate("MainWindow", u"Show advanced render settings.", None))
#endif // QT_CONFIG(tooltip)
        self.show_advanced.setText(QCoreApplication.translate("MainWindow", u"Advanced", None))
        self.tab_options.setTabText(self.tab_options.indexOf(self.tab), QCoreApplication.translate("MainWindow", u"Main", None))
        self.opts_status.setTitle(QCoreApplication.translate("MainWindow", u"Status", None))
#if QT_CONFIG(tooltip)
        self.profile_modified.setToolTip(QCoreApplication.translate("MainWindow", u"Indicates if the selected profile has unsaved changes.", None))
#endif // QT_CONFIG(tooltip)
        self.profile_modified.setText(QCoreApplication.translate("MainWindow", u"Yes", None))
#if QT_CONFIG(tooltip)
        self.profile_save.setToolTip(QCoreApplication.translate("MainWindow", u"Save the selected profile.", None))
#endif // QT_CONFIG(tooltip)
        self.profile_save.setText(QCoreApplication.translate("MainWindow", u"Save", None))
#if QT_CONFIG(tooltip)
        self.label_13.setToolTip(QCoreApplication.translate("MainWindow", u"!inherit profile_modified", None))
#endif // QT_CONFIG(tooltip)
        self.label_13.setText(QCoreApplication.translate("MainWindow", u"Modified:", None))
        self.opts_resolution.setTitle(QCoreApplication.translate("MainWindow", u"Resolutions", None))
        self.label_17.setText(QCoreApplication.translate("MainWindow", u"Choose which resolutions should be visible in the render.", None))
        self.label_15.setText(QCoreApplication.translate("MainWindow", u"2.5%", None))
        self.checkBox_2.setText(QCoreApplication.translate("MainWindow", u"1920x1080", None))
        self.checkBox.setText(QCoreApplication.translate("MainWindow", u"2560x1440", None))
        self.label_2.setText(QCoreApplication.translate("MainWindow", u"97.2%", None))
        self.checkBox_4.setText(QCoreApplication.translate("MainWindow", u"1080x1920", None))
        self.label_3.setText(QCoreApplication.translate("MainWindow", u"0.3%", None))
#if QT_CONFIG(tooltip)
        self.opts_monitor.setToolTip(QCoreApplication.translate("MainWindow", u"Set how multiple monitors are handled.", None))
#endif // QT_CONFIG(tooltip)
        self.opts_monitor.setTitle(QCoreApplication.translate("MainWindow", u"Override Multiple Monitors Mode", None))
        self.label_26.setText(QCoreApplication.translate("MainWindow", u"Choose how to handle multiple monitors for this profile.", None))
        self.label_27.setText(QCoreApplication.translate("MainWindow", u"Changing this setting only affects how new data is recorded.", None))
#if QT_CONFIG(tooltip)
        self.multi_monitor.setToolTip(QCoreApplication.translate("MainWindow", u"Record each monitor and overlap the data.\n"
"This is the default behaviour.", None))
#endif // QT_CONFIG(tooltip)
        self.multi_monitor.setText(QCoreApplication.translate("MainWindow", u"Record each monitor independently", None))
#if QT_CONFIG(tooltip)
        self.single_monitor.setToolTip(QCoreApplication.translate("MainWindow", u"Treat all connected monitors as part of the same display.", None))
#endif // QT_CONFIG(tooltip)
        self.single_monitor.setText(QCoreApplication.translate("MainWindow", u"Combine as one large display", None))
        self.opts_tracking.setTitle(QCoreApplication.translate("MainWindow", u"Tracking", None))
        self.label_25.setText(QCoreApplication.translate("MainWindow", u"Choose which data should be tracked.", None))
#if QT_CONFIG(tooltip)
        self.track_mouse.setToolTip(QCoreApplication.translate("MainWindow", u"Enable or disable mouse tracking for the selected profile.", None))
#endif // QT_CONFIG(tooltip)
        self.track_mouse.setText(QCoreApplication.translate("MainWindow", u"Track Mouse", None))
#if QT_CONFIG(tooltip)
        self.delete_mouse.setToolTip(QCoreApplication.translate("MainWindow", u"Delete all mouse data for the current profile.\n"
"\n"
"As a safety precaution, this option is disabled while\n"
"mouse tracking is enabled.", None))
#endif // QT_CONFIG(tooltip)
        self.delete_mouse.setText(QCoreApplication.translate("MainWindow", u"Delete Data", None))
#if QT_CONFIG(tooltip)
        self.track_keyboard.setToolTip(QCoreApplication.translate("MainWindow", u"Enable or disable keyboard tracking for the selected profile.", None))
#endif // QT_CONFIG(tooltip)
        self.track_keyboard.setText(QCoreApplication.translate("MainWindow", u"Track Keyboard", None))
#if QT_CONFIG(tooltip)
        self.delete_keyboard.setToolTip(QCoreApplication.translate("MainWindow", u"Delete all keyboard data for the current profile.\n"
"\n"
"As a safety precaution, this option is disabled while\n"
"keyboard tracking is enabled.", None))
#endif // QT_CONFIG(tooltip)
        self.delete_keyboard.setText(QCoreApplication.translate("MainWindow", u"Delete Data", None))
#if QT_CONFIG(tooltip)
        self.track_gamepad.setToolTip(QCoreApplication.translate("MainWindow", u"Enable or disable gamepad tracking for the selected profile.", None))
#endif // QT_CONFIG(tooltip)
        self.track_gamepad.setText(QCoreApplication.translate("MainWindow", u"Track Gamepads", None))
#if QT_CONFIG(tooltip)
        self.delete_gamepad.setToolTip(QCoreApplication.translate("MainWindow", u"Delete all gamepad data for the current profile.\n"
"\n"
"As a safety precaution, this option is disabled while\n"
"gamepad tracking is enabled.", None))
#endif // QT_CONFIG(tooltip)
        self.delete_gamepad.setText(QCoreApplication.translate("MainWindow", u"Delete Data", None))
#if QT_CONFIG(tooltip)
        self.track_network.setToolTip(QCoreApplication.translate("MainWindow", u"Enable or disable network tracking for the selected profile.", None))
#endif // QT_CONFIG(tooltip)
        self.track_network.setText(QCoreApplication.translate("MainWindow", u"Track Network", None))
#if QT_CONFIG(tooltip)
        self.delete_network.setToolTip(QCoreApplication.translate("MainWindow", u"Delete all network data for the current profile.\n"
"\n"
"As a safety precaution, this option is disabled while\n"
"network tracking is enabled.", None))
#endif // QT_CONFIG(tooltip)
        self.delete_network.setText(QCoreApplication.translate("MainWindow", u"Delete Data", None))
#if QT_CONFIG(tooltip)
        self.delete_profile.setToolTip(QCoreApplication.translate("MainWindow", u"Delete the entire profile from disk.\n"
"\n"
"As a safety precaution, this option is disabled while\n"
"any tracking is enabled.\n"
"", None))
#endif // QT_CONFIG(tooltip)
        self.delete_profile.setText(QCoreApplication.translate("MainWindow", u"Delete Profile", None))
        self.tab_options.setTabText(self.tab_options.indexOf(self.tab_profile_options), QCoreApplication.translate("MainWindow", u"Profile Options", None))
#if QT_CONFIG(tooltip)
        self.groupBox_11.setToolTip(QCoreApplication.translate("MainWindow", u"Shows the details of the currently focused application.\n"
"This can be useful if adding a profile for a new application.", None))
#endif // QT_CONFIG(tooltip)
        self.groupBox_11.setTitle(QCoreApplication.translate("MainWindow", u"Current Application", None))
        self.stat_app_title.setText(QCoreApplication.translate("MainWindow", u"Qt Widgets Designer", None))
        self.stat_app_exe.setText(QCoreApplication.translate("MainWindow", u"designer.exe", None))
        self.label_10.setText(QCoreApplication.translate("MainWindow", u"Window Name", None))
        self.label_5.setText(QCoreApplication.translate("MainWindow", u"Executable", None))
        self.label_6.setText(QCoreApplication.translate("MainWindow", u"Tracked", None))
        self.stat_app_tracked.setText(QCoreApplication.translate("MainWindow", u"No", None))
#if QT_CONFIG(tooltip)
        self.stat_app_add.setToolTip(QCoreApplication.translate("MainWindow", u"Add a new tracked application.", None))
#endif // QT_CONFIG(tooltip)
        self.stat_app_add.setText(QCoreApplication.translate("MainWindow", u"Add Tracked Application", None))
#if QT_CONFIG(tooltip)
        self.groupBox_10.setToolTip(QCoreApplication.translate("MainWindow", u"Displays how long since actions have occurred.\n"
"Clicking the button will trigger a manual update.", None))
#endif // QT_CONFIG(tooltip)
        self.groupBox_10.setTitle(QCoreApplication.translate("MainWindow", u"Time Since", None))
#if QT_CONFIG(tooltip)
        self.time_since_thumbnail.setToolTip(QCoreApplication.translate("MainWindow", u"How many seconds since the render preview was updated.", None))
#endif // QT_CONFIG(tooltip)
        self.time_since_thumbnail.setText(QCoreApplication.translate("MainWindow", u"5.4s", None))
#if QT_CONFIG(tooltip)
        self.save.setToolTip(QCoreApplication.translate("MainWindow", u"Save all modified profiles.", None))
#endif // QT_CONFIG(tooltip)
        self.save.setText(QCoreApplication.translate("MainWindow", u"Save", None))
#if QT_CONFIG(tooltip)
        self.thumbnail_refresh.setToolTip(QCoreApplication.translate("MainWindow", u"Request a render preview update.", None))
#endif // QT_CONFIG(tooltip)
        self.thumbnail_refresh.setText(QCoreApplication.translate("MainWindow", u"Preview Render", None))
#if QT_CONFIG(tooltip)
        self.time_since_save.setToolTip(QCoreApplication.translate("MainWindow", u"How many seconds since the last save.", None))
#endif // QT_CONFIG(tooltip)
        self.time_since_save.setText(QCoreApplication.translate("MainWindow", u"23.5s", None))
#if QT_CONFIG(tooltip)
        self.autosave.setToolTip(QCoreApplication.translate("MainWindow", u"Enable or disable autosaving.", None))
#endif // QT_CONFIG(tooltip)
        self.autosave.setText(QCoreApplication.translate("MainWindow", u"Autosave", None))
#if QT_CONFIG(tooltip)
        self.time_since_applist_reload.setToolTip(QCoreApplication.translate("MainWindow", u"How many seconds since AppList.txt was read from disk.", None))
#endif // QT_CONFIG(tooltip)
        self.time_since_applist_reload.setText(QCoreApplication.translate("MainWindow", u"4m 12s", None))
#if QT_CONFIG(tooltip)
        self.applist_reload.setToolTip(QCoreApplication.translate("MainWindow", u"Trigger a reload of AppList.txt.\n"
"This should be used after manually editing it.", None))
#endif // QT_CONFIG(tooltip)
        self.applist_reload.setText(QCoreApplication.translate("MainWindow", u"Applist Reload", None))
#if QT_CONFIG(tooltip)
        self.status_components.setToolTip(QCoreApplication.translate("MainWindow", u"Show the state of each component.", None))
#endif // QT_CONFIG(tooltip)
        self.status_components.setTitle(QCoreApplication.translate("MainWindow", u"Components", None))
        self.status_hub_state.setText(QCoreApplication.translate("MainWindow", u"Running", None))
        self.status_app_state.setText(QCoreApplication.translate("MainWindow", u"Running", None))
        self.status_hub_pid.setText("")
        self.status_tracking_state.setText(QCoreApplication.translate("MainWindow", u"Running", None))
        self.status_header_name.setText(QCoreApplication.translate("MainWindow", u"**Name**", None))
        self.status_gui_name.setText(QCoreApplication.translate("MainWindow", u"GUI", None))
        self.status_processing_pid.setText("")
        self.status_header_state.setText(QCoreApplication.translate("MainWindow", u"**State**", None))
        self.status_app_pid.setText("")
        self.status_hub_name.setText(QCoreApplication.translate("MainWindow", u"Hub", None))
        self.status_header_pid.setText(QCoreApplication.translate("MainWindow", u"**PID**", None))
        self.status_app_name.setText(QCoreApplication.translate("MainWindow", u"App Detection", None))
        self.status_tracking_name.setText(QCoreApplication.translate("MainWindow", u"Tracking", None))
        self.status_processing_state.setText(QCoreApplication.translate("MainWindow", u"Busy", None))
        self.status_gui_state.setText(QCoreApplication.translate("MainWindow", u"Running", None))
        self.status_processing_name.setText(QCoreApplication.translate("MainWindow", u"Processing", None))
        self.status_tracking_pid.setText("")
        self.status_gui_pid.setText("")
        self.status_header_queue.setText(QCoreApplication.translate("MainWindow", u"**Queue**", None))
        self.status_hub_queue.setText(QCoreApplication.translate("MainWindow", u"0", None))
        self.status_tracking_queue.setText(QCoreApplication.translate("MainWindow", u"3", None))
        self.status_processing_queue.setText(QCoreApplication.translate("MainWindow", u"642", None))
        self.status_gui_queue.setText(QCoreApplication.translate("MainWindow", u"0", None))
        self.status_app_queue.setText(QCoreApplication.translate("MainWindow", u"0", None))
        self.tab_options.setTabText(self.tab_options.indexOf(self.tab_4), QCoreApplication.translate("MainWindow", u"Status", None))

        __sortingEnabled1 = self.listWidget_3.isSortingEnabled()
        self.listWidget_3.setSortingEnabled(False)
        ___qlistwidgetitem2 = self.listWidget_3.item(0)
        ___qlistwidgetitem2.setText(QCoreApplication.translate("MainWindow", u"[11:05:38] Left mouse button being held at (1480, 730).", None));
        ___qlistwidgetitem3 = self.listWidget_3.item(1)
        ___qlistwidgetitem3.setText(QCoreApplication.translate("MainWindow", u"[11:05:38] Left mouse button being held at (1454, 658).", None));
        ___qlistwidgetitem4 = self.listWidget_3.item(2)
        ___qlistwidgetitem4.setText(QCoreApplication.translate("MainWindow", u"[11:05:38] Left mouse button being held at (1447, 639).", None));
        ___qlistwidgetitem5 = self.listWidget_3.item(3)
        ___qlistwidgetitem5.setText(QCoreApplication.translate("MainWindow", u"[11:05:38] Left mouse button being held at (1447, 639).", None));
        ___qlistwidgetitem6 = self.listWidget_3.item(4)
        ___qlistwidgetitem6.setText(QCoreApplication.translate("MainWindow", u"[11:05:40] Left mouse button clicked at (1448, 835).", None));
        ___qlistwidgetitem7 = self.listWidget_3.item(5)
        ___qlistwidgetitem7.setText(QCoreApplication.translate("MainWindow", u"[11:05:40] Left mouse button being held at (1427, 740).", None));
        ___qlistwidgetitem8 = self.listWidget_3.item(6)
        ___qlistwidgetitem8.setText(QCoreApplication.translate("MainWindow", u"[11:05:40] Left mouse button being held at (1424, 660).", None));
        ___qlistwidgetitem9 = self.listWidget_3.item(7)
        ___qlistwidgetitem9.setText(QCoreApplication.translate("MainWindow", u"[11:05:40] Left mouse button being held at (1425, 643).", None));
        ___qlistwidgetitem10 = self.listWidget_3.item(8)
        ___qlistwidgetitem10.setText(QCoreApplication.translate("MainWindow", u"[11:05:41] Left mouse button being held at (1425, 643).", None));
        ___qlistwidgetitem11 = self.listWidget_3.item(9)
        ___qlistwidgetitem11.setText(QCoreApplication.translate("MainWindow", u"[11:05:41] Finished loading data. | 170 commands queued for processing.", None));
        ___qlistwidgetitem12 = self.listWidget_3.item(10)
        ___qlistwidgetitem12.setText(QCoreApplication.translate("MainWindow", u"[11:05:43] Left mouse button clicked at (1109, 705).", None));
        ___qlistwidgetitem13 = self.listWidget_3.item(11)
        ___qlistwidgetitem13.setText(QCoreApplication.translate("MainWindow", u"[11:05:44] Application gained focus: Qt Designer | Application resolution is 2576x1416.", None));
        ___qlistwidgetitem14 = self.listWidget_3.item(12)
        ___qlistwidgetitem14.setText(QCoreApplication.translate("MainWindow", u"[11:05:44] Switching profile to Qt Designer. | Preparing data to save...", None));
        ___qlistwidgetitem15 = self.listWidget_3.item(13)
        ___qlistwidgetitem15.setText(QCoreApplication.translate("MainWindow", u"[11:05:44] Left mouse button clicked at (1493, 996).", None));
        ___qlistwidgetitem16 = self.listWidget_3.item(14)
        ___qlistwidgetitem16.setText(QCoreApplication.translate("MainWindow", u"[11:05:45] Left mouse button clicked at (1506, 1024).", None));
        ___qlistwidgetitem17 = self.listWidget_3.item(15)
        ___qlistwidgetitem17.setText(QCoreApplication.translate("MainWindow", u"[11:05:51] Left mouse button clicked at (781, 412).", None));
        ___qlistwidgetitem18 = self.listWidget_3.item(16)
        ___qlistwidgetitem18.setText(QCoreApplication.translate("MainWindow", u"[11:05:55] Left mouse button clicked at (2128, 162).", None));
        ___qlistwidgetitem19 = self.listWidget_3.item(17)
        ___qlistwidgetitem19.setText(QCoreApplication.translate("MainWindow", u"[11:05:56] 348 commands queued for processing.", None));
        ___qlistwidgetitem20 = self.listWidget_3.item(18)
        ___qlistwidgetitem20.setText(QCoreApplication.translate("MainWindow", u"[11:06:02] Left mouse button clicked at (89, 535).", None));
        self.listWidget_3.setSortingEnabled(__sortingEnabled1)

        self.output_logs.setTabText(self.output_logs.indexOf(self.tab_6), QCoreApplication.translate("MainWindow", u"Tracking", None))
        self.output_logs.setTabText(self.output_logs.indexOf(self.tab_7), QCoreApplication.translate("MainWindow", u"Processing", None))
        self.menuFile.setTitle(QCoreApplication.translate("MainWindow", u"File", None))
        self.menuExport.setTitle(QCoreApplication.translate("MainWindow", u"Export", None))
        self.menuHelp.setTitle(QCoreApplication.translate("MainWindow", u"Help", None))
        self.menuPreferences.setTitle(QCoreApplication.translate("MainWindow", u"Preferences", None))
        self.menuStartup.setTitle(QCoreApplication.translate("MainWindow", u"Startup", None))
        self.tray_context_menu.setTitle(QCoreApplication.translate("MainWindow", u"_Tray_", None))
        self.menu_debug.setTitle(QCoreApplication.translate("MainWindow", u"Debug", None))
        self.menu_debug_state.setTitle(QCoreApplication.translate("MainWindow", u"Set Tracking State", None))
        self.menu_debug_raise.setTitle(QCoreApplication.translate("MainWindow", u"Raise Exception", None))
        self.menuTracking.setTitle(QCoreApplication.translate("MainWindow", u"Tracking", None))
    # retranslateUi

