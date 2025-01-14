# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'mainUzuWKR.ui'
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QGridLayout,
    QGroupBox, QHBoxLayout, QLabel, QListWidget,
    QListWidgetItem, QMainWindow, QMenu, QMenuBar,
    QPushButton, QScrollArea, QScrollBar, QSizePolicy,
    QSlider, QSpacerItem, QSpinBox, QSplitter,
    QStatusBar, QTabWidget, QVBoxLayout, QWidget)

from mousetracks2.ui.widgets import ResizableImage

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(736, 468)
        self.actionShow_Log = QAction(MainWindow)
        self.actionShow_Log.setObjectName(u"actionShow_Log")
        self.actionShow_Log.setCheckable(True)
        self.actionShow_Log.setChecked(True)
        self.actionShow_Log.setEnabled(False)
        self.file_save = QAction(MainWindow)
        self.file_save.setObjectName(u"file_save")
        self.actionExport = QAction(MainWindow)
        self.actionExport.setObjectName(u"actionExport")
        self.actionExport.setEnabled(False)
        self.actionImport = QAction(MainWindow)
        self.actionImport.setObjectName(u"actionImport")
        self.actionImport.setEnabled(False)
        self.actionAbout = QAction(MainWindow)
        self.actionAbout.setObjectName(u"actionAbout")
        self.actionAbout.setEnabled(False)
        self.actionDocumentation = QAction(MainWindow)
        self.actionDocumentation.setObjectName(u"actionDocumentation")
        self.actionDocumentation.setEnabled(False)
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
        self.debug_tracking_start = QAction(MainWindow)
        self.debug_tracking_start.setObjectName(u"debug_tracking_start")
        self.debug_tracking_pause = QAction(MainWindow)
        self.debug_tracking_pause.setObjectName(u"debug_tracking_pause")
        self.debug_tracking_stop = QAction(MainWindow)
        self.debug_tracking_stop.setObjectName(u"debug_tracking_stop")
        self.debug_raise_tracking = QAction(MainWindow)
        self.debug_raise_tracking.setObjectName(u"debug_raise_tracking")
        self.debug_raise_processing = QAction(MainWindow)
        self.debug_raise_processing.setObjectName(u"debug_raise_processing")
        self.debug_raise_hub = QAction(MainWindow)
        self.debug_raise_hub.setObjectName(u"debug_raise_hub")
        self.debug_raise_gui = QAction(MainWindow)
        self.debug_raise_gui.setObjectName(u"debug_raise_gui")
        self.debug_raise_app = QAction(MainWindow)
        self.debug_raise_app.setObjectName(u"debug_raise_app")
        self.actionRestart = QAction(MainWindow)
        self.actionRestart.setObjectName(u"actionRestart")
        self.actionRestart.setEnabled(False)
        self.actionSave_Image = QAction(MainWindow)
        self.actionSave_Image.setObjectName(u"actionSave_Image")
        self.actionVisit_Website = QAction(MainWindow)
        self.actionVisit_Website.setObjectName(u"actionVisit_Website")
        self.actionVisit_Reddit = QAction(MainWindow)
        self.actionVisit_Reddit.setObjectName(u"actionVisit_Reddit")
        self.actionVisit_Facebook = QAction(MainWindow)
        self.actionVisit_Facebook.setObjectName(u"actionVisit_Facebook")
        self.actionWebsite = QAction(MainWindow)
        self.actionWebsite.setObjectName(u"actionWebsite")
        self.actionWebsite.setEnabled(False)
        self.actionReddit = QAction(MainWindow)
        self.actionReddit.setObjectName(u"actionReddit")
        self.actionReddit.setEnabled(False)
        self.actionFacebook = QAction(MainWindow)
        self.actionFacebook.setObjectName(u"actionFacebook")
        self.actionFacebook.setEnabled(False)
        self.tray_exit = QAction(MainWindow)
        self.tray_exit.setObjectName(u"tray_exit")
        self.tray_show = QAction(MainWindow)
        self.tray_show.setObjectName(u"tray_show")
        self.tray_hide = QAction(MainWindow)
        self.tray_hide.setObjectName(u"tray_hide")
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.verticalLayout_6 = QVBoxLayout(self.centralwidget)
        self.verticalLayout_6.setObjectName(u"verticalLayout_6")
        self.splitter_2 = QSplitter(self.centralwidget)
        self.splitter_2.setObjectName(u"splitter_2")
        self.splitter_2.setOrientation(Qt.Orientation.Vertical)
        self.splitter = QSplitter(self.splitter_2)
        self.splitter.setObjectName(u"splitter")
        self.splitter.setOrientation(Qt.Orientation.Horizontal)
        self.widget = QWidget(self.splitter)
        self.widget.setObjectName(u"widget")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(2)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.widget.sizePolicy().hasHeightForWidth())
        self.widget.setSizePolicy(sizePolicy)
        self.verticalLayout_4 = QVBoxLayout(self.widget)
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.thumbnail = ResizableImage(self.widget)
        self.thumbnail.setObjectName(u"thumbnail")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.thumbnail.sizePolicy().hasHeightForWidth())
        self.thumbnail.setSizePolicy(sizePolicy1)

        self.verticalLayout_4.addWidget(self.thumbnail)

        self.save_render = QPushButton(self.widget)
        self.save_render.setObjectName(u"save_render")
        sizePolicy2 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.save_render.sizePolicy().hasHeightForWidth())
        self.save_render.setSizePolicy(sizePolicy2)

        self.verticalLayout_4.addWidget(self.save_render)

        self.splitter.addWidget(self.widget)
        self.tabWidget = QTabWidget(self.splitter)
        self.tabWidget.setObjectName(u"tabWidget")
        sizePolicy3 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        sizePolicy3.setHorizontalStretch(0)
        sizePolicy3.setVerticalStretch(0)
        sizePolicy3.setHeightForWidth(self.tabWidget.sizePolicy().hasHeightForWidth())
        self.tabWidget.setSizePolicy(sizePolicy3)
        self.tabWidget.setMinimumSize(QSize(300, 0))
        self.tab = QWidget()
        self.tab.setObjectName(u"tab")
        self.verticalLayout_2 = QVBoxLayout(self.tab)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.scrollArea = QScrollArea(self.tab)
        self.scrollArea.setObjectName(u"scrollArea")
        self.scrollArea.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName(u"scrollAreaWidgetContents")
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 257, 492))
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
        sizePolicy2.setHeightForWidth(self.current_profile.sizePolicy().hasHeightForWidth())
        self.current_profile.setSizePolicy(sizePolicy2)

        self.verticalLayout_9.addWidget(self.current_profile)

        self.auto_switch_profile = QCheckBox(self.groupBox_2)
        self.auto_switch_profile.setObjectName(u"auto_switch_profile")
        self.auto_switch_profile.setChecked(True)

        self.verticalLayout_9.addWidget(self.auto_switch_profile)


        self.verticalLayout_3.addWidget(self.groupBox_2)

        self.groupBox_3 = QGroupBox(self.scrollAreaWidgetContents)
        self.groupBox_3.setObjectName(u"groupBox_3")
        self.gridLayout_6 = QGridLayout(self.groupBox_3)
        self.gridLayout_6.setObjectName(u"gridLayout_6")
        self.map_type = QComboBox(self.groupBox_3)
        self.map_type.setObjectName(u"map_type")

        self.gridLayout_6.addWidget(self.map_type, 0, 0, 1, 1)


        self.verticalLayout_3.addWidget(self.groupBox_3)

        self.groupBox_4 = QGroupBox(self.scrollAreaWidgetContents)
        self.groupBox_4.setObjectName(u"groupBox_4")
        self.horizontalLayout_2 = QHBoxLayout(self.groupBox_4)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.colour_option = QComboBox(self.groupBox_4)
        self.colour_option.addItem("")
        self.colour_option.addItem("")
        self.colour_option.addItem("")
        self.colour_option.setObjectName(u"colour_option")
        self.colour_option.setEditable(True)

        self.horizontalLayout_2.addWidget(self.colour_option)


        self.verticalLayout_3.addWidget(self.groupBox_4)

        self.groupBox_9 = QGroupBox(self.scrollAreaWidgetContents)
        self.groupBox_9.setObjectName(u"groupBox_9")
        self.gridLayout_3 = QGridLayout(self.groupBox_9)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.label_8 = QLabel(self.groupBox_9)
        self.label_8.setObjectName(u"label_8")
        self.label_8.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout_3.addWidget(self.label_8, 9, 0, 1, 1)

        self.stat_download_total = QLabel(self.groupBox_9)
        self.stat_download_total.setObjectName(u"stat_download_total")

        self.gridLayout_3.addWidget(self.stat_download_total, 8, 1, 1, 1)

        self.stat_clicks = QLabel(self.groupBox_9)
        self.stat_clicks.setObjectName(u"stat_clicks")

        self.gridLayout_3.addWidget(self.stat_clicks, 0, 1, 1, 1)

        self.label_21 = QLabel(self.groupBox_9)
        self.label_21.setObjectName(u"label_21")
        self.label_21.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout_3.addWidget(self.label_21, 0, 0, 1, 1)

        self.label_22 = QLabel(self.groupBox_9)
        self.label_22.setObjectName(u"label_22")
        self.label_22.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout_3.addWidget(self.label_22, 6, 0, 1, 1)

        self.label_23 = QLabel(self.groupBox_9)
        self.label_23.setObjectName(u"label_23")
        self.label_23.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout_3.addWidget(self.label_23, 7, 0, 1, 1)

        self.label_19 = QLabel(self.groupBox_9)
        self.label_19.setObjectName(u"label_19")
        self.label_19.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout_3.addWidget(self.label_19, 4, 0, 1, 1)

        self.label = QLabel(self.groupBox_9)
        self.label.setObjectName(u"label")
        self.label.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout_3.addWidget(self.label, 3, 0, 1, 1)

        self.stat_active = QLabel(self.groupBox_9)
        self.stat_active.setObjectName(u"stat_active")

        self.gridLayout_3.addWidget(self.stat_active, 6, 1, 1, 1)

        self.stat_keys = QLabel(self.groupBox_9)
        self.stat_keys.setObjectName(u"stat_keys")

        self.gridLayout_3.addWidget(self.stat_keys, 2, 1, 1, 1)

        self.label_20 = QLabel(self.groupBox_9)
        self.label_20.setObjectName(u"label_20")
        self.label_20.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout_3.addWidget(self.label_20, 2, 0, 1, 1)

        self.label_9 = QLabel(self.groupBox_9)
        self.label_9.setObjectName(u"label_9")
        self.label_9.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout_3.addWidget(self.label_9, 1, 0, 1, 1)

        self.stat_buttons = QLabel(self.groupBox_9)
        self.stat_buttons.setObjectName(u"stat_buttons")

        self.gridLayout_3.addWidget(self.stat_buttons, 3, 1, 1, 1)

        self.stat_inactive = QLabel(self.groupBox_9)
        self.stat_inactive.setObjectName(u"stat_inactive")

        self.gridLayout_3.addWidget(self.stat_inactive, 7, 1, 1, 1)

        self.label_4 = QLabel(self.groupBox_9)
        self.label_4.setObjectName(u"label_4")
        self.label_4.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout_3.addWidget(self.label_4, 8, 0, 1, 1)

        self.stat_scroll = QLabel(self.groupBox_9)
        self.stat_scroll.setObjectName(u"stat_scroll")

        self.gridLayout_3.addWidget(self.stat_scroll, 1, 1, 1, 1)

        self.stat_distance = QLabel(self.groupBox_9)
        self.stat_distance.setObjectName(u"stat_distance")

        self.gridLayout_3.addWidget(self.stat_distance, 4, 1, 1, 1)

        self.stat_upload_total = QLabel(self.groupBox_9)
        self.stat_upload_total.setObjectName(u"stat_upload_total")

        self.gridLayout_3.addWidget(self.stat_upload_total, 9, 1, 1, 1)

        self.label_11 = QLabel(self.groupBox_9)
        self.label_11.setObjectName(u"label_11")
        self.label_11.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout_3.addWidget(self.label_11, 5, 0, 1, 1)

        self.stat_elapsed = QLabel(self.groupBox_9)
        self.stat_elapsed.setObjectName(u"stat_elapsed")

        self.gridLayout_3.addWidget(self.stat_elapsed, 5, 1, 1, 1)


        self.verticalLayout_3.addWidget(self.groupBox_9)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_3.addItem(self.verticalSpacer)

        self.scrollArea.setWidget(self.scrollAreaWidgetContents)

        self.verticalLayout_2.addWidget(self.scrollArea)

        self.horizontalLayout_5 = QHBoxLayout()
        self.horizontalLayout_5.setObjectName(u"horizontalLayout_5")
        self.tracking_start = QPushButton(self.tab)
        self.tracking_start.setObjectName(u"tracking_start")

        self.horizontalLayout_5.addWidget(self.tracking_start)

        self.tracking_pause = QPushButton(self.tab)
        self.tracking_pause.setObjectName(u"tracking_pause")

        self.horizontalLayout_5.addWidget(self.tracking_pause)


        self.verticalLayout_2.addLayout(self.horizontalLayout_5)

        self.tabWidget.addTab(self.tab, "")
        self.tab_3 = QWidget()
        self.tab_3.setObjectName(u"tab_3")
        self.verticalLayout_8 = QVBoxLayout(self.tab_3)
        self.verticalLayout_8.setObjectName(u"verticalLayout_8")
        self.scrollArea_4 = QScrollArea(self.tab_3)
        self.scrollArea_4.setObjectName(u"scrollArea_4")
        self.scrollArea_4.setWidgetResizable(True)
        self.scrollAreaWidgetContents_4 = QWidget()
        self.scrollAreaWidgetContents_4.setObjectName(u"scrollAreaWidgetContents_4")
        self.scrollAreaWidgetContents_4.setGeometry(QRect(0, 0, 261, 235))
        self.verticalLayout_7 = QVBoxLayout(self.scrollAreaWidgetContents_4)
        self.verticalLayout_7.setObjectName(u"verticalLayout_7")
        self.custom_resolution = QGroupBox(self.scrollAreaWidgetContents_4)
        self.custom_resolution.setObjectName(u"custom_resolution")
        self.custom_resolution.setEnabled(False)
        self.custom_resolution.setCheckable(True)
        self.custom_resolution.setChecked(False)
        self.horizontalLayout_4 = QHBoxLayout(self.custom_resolution)
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.custom_width = QSpinBox(self.custom_resolution)
        self.custom_width.setObjectName(u"custom_width")
        self.custom_width.setSuffix(u"px")
        self.custom_width.setMinimum(1)
        self.custom_width.setMaximum(999999)
        self.custom_width.setSingleStep(16)
        self.custom_width.setValue(1920)

        self.horizontalLayout_4.addWidget(self.custom_width)

        self.custom_height = QSpinBox(self.custom_resolution)
        self.custom_height.setObjectName(u"custom_height")
        self.custom_height.setSuffix(u"px")
        self.custom_height.setMinimum(1)
        self.custom_height.setMaximum(999999)
        self.custom_height.setSingleStep(9)
        self.custom_height.setValue(1080)

        self.horizontalLayout_4.addWidget(self.custom_height)


        self.verticalLayout_7.addWidget(self.custom_resolution)

        self.groupBox_5 = QGroupBox(self.scrollAreaWidgetContents_4)
        self.groupBox_5.setObjectName(u"groupBox_5")
        self.horizontalLayout_3 = QHBoxLayout(self.groupBox_5)
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.render_samples = QSlider(self.groupBox_5)
        self.render_samples.setObjectName(u"render_samples")
        self.render_samples.setMinimum(1)
        self.render_samples.setMaximum(8)
        self.render_samples.setPageStep(1)
        self.render_samples.setSliderPosition(4)
        self.render_samples.setOrientation(Qt.Orientation.Horizontal)

        self.horizontalLayout_3.addWidget(self.render_samples)

        self.label_2 = QLabel(self.groupBox_5)
        self.label_2.setObjectName(u"label_2")

        self.horizontalLayout_3.addWidget(self.label_2)


        self.verticalLayout_7.addWidget(self.groupBox_5)

        self.record_history = QGroupBox(self.scrollAreaWidgetContents_4)
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


        self.verticalLayout_7.addWidget(self.record_history)

        self.verticalSpacer_3 = QSpacerItem(20, 226, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_7.addItem(self.verticalSpacer_3)

        self.scrollArea_4.setWidget(self.scrollAreaWidgetContents_4)

        self.verticalLayout_8.addWidget(self.scrollArea_4)

        self.tabWidget.addTab(self.tab_3, "")
        self.tab_4 = QWidget()
        self.tab_4.setObjectName(u"tab_4")
        self.verticalLayout_10 = QVBoxLayout(self.tab_4)
        self.verticalLayout_10.setObjectName(u"verticalLayout_10")
        self.scrollArea_3 = QScrollArea(self.tab_4)
        self.scrollArea_3.setObjectName(u"scrollArea_3")
        self.scrollArea_3.setWidgetResizable(True)
        self.scrollAreaWidgetContents_3 = QWidget()
        self.scrollAreaWidgetContents_3.setObjectName(u"scrollAreaWidgetContents_3")
        self.scrollAreaWidgetContents_3.setGeometry(QRect(0, -84, 257, 494))
        self.verticalLayout = QVBoxLayout(self.scrollAreaWidgetContents_3)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.groupBox_11 = QGroupBox(self.scrollAreaWidgetContents_3)
        self.groupBox_11.setObjectName(u"groupBox_11")
        self.groupBox_11.setEnabled(False)
        self.gridLayout_5 = QGridLayout(self.groupBox_11)
        self.gridLayout_5.setObjectName(u"gridLayout_5")
        self.label_6 = QLabel(self.groupBox_11)
        self.label_6.setObjectName(u"label_6")

        self.gridLayout_5.addWidget(self.label_6, 2, 0, 1, 1)

        self.label_10 = QLabel(self.groupBox_11)
        self.label_10.setObjectName(u"label_10")

        self.gridLayout_5.addWidget(self.label_10, 1, 0, 1, 1)

        self.label_5 = QLabel(self.groupBox_11)
        self.label_5.setObjectName(u"label_5")

        self.gridLayout_5.addWidget(self.label_5, 0, 0, 1, 1)

        self.stat_app_exe = QLabel(self.groupBox_11)
        self.stat_app_exe.setObjectName(u"stat_app_exe")

        self.gridLayout_5.addWidget(self.stat_app_exe, 0, 1, 1, 1)

        self.stat_app_window_name = QLabel(self.groupBox_11)
        self.stat_app_window_name.setObjectName(u"stat_app_window_name")

        self.gridLayout_5.addWidget(self.stat_app_window_name, 1, 1, 1, 1)

        self.stat_app_tracked = QLabel(self.groupBox_11)
        self.stat_app_tracked.setObjectName(u"stat_app_tracked")

        self.gridLayout_5.addWidget(self.stat_app_tracked, 2, 1, 1, 1)


        self.verticalLayout.addWidget(self.groupBox_11)

        self.groupBox_10 = QGroupBox(self.scrollAreaWidgetContents_3)
        self.groupBox_10.setObjectName(u"groupBox_10")
        self.gridLayout_4 = QGridLayout(self.groupBox_10)
        self.gridLayout_4.setObjectName(u"gridLayout_4")
        self.save = QPushButton(self.groupBox_10)
        self.save.setObjectName(u"save")

        self.gridLayout_4.addWidget(self.save, 0, 0, 1, 1)

        self.pushButton = QPushButton(self.groupBox_10)
        self.pushButton.setObjectName(u"pushButton")
        self.pushButton.setEnabled(False)

        self.gridLayout_4.addWidget(self.pushButton, 2, 0, 1, 1)

        self.thumbnail_refresh = QPushButton(self.groupBox_10)
        self.thumbnail_refresh.setObjectName(u"thumbnail_refresh")

        self.gridLayout_4.addWidget(self.thumbnail_refresh, 1, 0, 1, 1)

        self.time_since_thumbnail = QLabel(self.groupBox_10)
        self.time_since_thumbnail.setObjectName(u"time_since_thumbnail")

        self.gridLayout_4.addWidget(self.time_since_thumbnail, 1, 1, 1, 1)

        self.label_3 = QLabel(self.groupBox_10)
        self.label_3.setObjectName(u"label_3")
        self.label_3.setEnabled(False)

        self.gridLayout_4.addWidget(self.label_3, 2, 1, 1, 1)

        self.time_since_save = QLabel(self.groupBox_10)
        self.time_since_save.setObjectName(u"time_since_save")

        self.gridLayout_4.addWidget(self.time_since_save, 0, 1, 1, 1)


        self.verticalLayout.addWidget(self.groupBox_10)

        self.groupBox_13 = QGroupBox(self.scrollAreaWidgetContents_3)
        self.groupBox_13.setObjectName(u"groupBox_13")
        self.groupBox_13.setEnabled(False)
        self.gridLayout_8 = QGridLayout(self.groupBox_13)
        self.gridLayout_8.setObjectName(u"gridLayout_8")
        self.stat_tracking_state = QLabel(self.groupBox_13)
        self.stat_tracking_state.setObjectName(u"stat_tracking_state")

        self.gridLayout_8.addWidget(self.stat_tracking_state, 0, 1, 1, 1)

        self.label_34 = QLabel(self.groupBox_13)
        self.label_34.setObjectName(u"label_34")

        self.gridLayout_8.addWidget(self.label_34, 0, 0, 1, 1)

        self.label_36 = QLabel(self.groupBox_13)
        self.label_36.setObjectName(u"label_36")

        self.gridLayout_8.addWidget(self.label_36, 2, 0, 1, 1)

        self.label_39 = QLabel(self.groupBox_13)
        self.label_39.setObjectName(u"label_39")

        self.gridLayout_8.addWidget(self.label_39, 1, 0, 1, 1)

        self.stat_app_state = QLabel(self.groupBox_13)
        self.stat_app_state.setObjectName(u"stat_app_state")

        self.gridLayout_8.addWidget(self.stat_app_state, 3, 1, 1, 1)

        self.stat_hub_state = QLabel(self.groupBox_13)
        self.stat_hub_state.setObjectName(u"stat_hub_state")

        self.gridLayout_8.addWidget(self.stat_hub_state, 2, 1, 1, 1)

        self.stat_processing_state = QLabel(self.groupBox_13)
        self.stat_processing_state.setObjectName(u"stat_processing_state")

        self.gridLayout_8.addWidget(self.stat_processing_state, 1, 1, 1, 1)

        self.label_40 = QLabel(self.groupBox_13)
        self.label_40.setObjectName(u"label_40")

        self.gridLayout_8.addWidget(self.label_40, 3, 0, 1, 1)


        self.verticalLayout.addWidget(self.groupBox_13)

        self.groupBox_14 = QGroupBox(self.scrollAreaWidgetContents_3)
        self.groupBox_14.setObjectName(u"groupBox_14")
        self.groupBox_14.setEnabled(False)
        self.gridLayout_9 = QGridLayout(self.groupBox_14)
        self.gridLayout_9.setObjectName(u"gridLayout_9")
        self.stat_tracking_queue = QLabel(self.groupBox_14)
        self.stat_tracking_queue.setObjectName(u"stat_tracking_queue")

        self.gridLayout_9.addWidget(self.stat_tracking_queue, 0, 1, 1, 1)

        self.label_45 = QLabel(self.groupBox_14)
        self.label_45.setObjectName(u"label_45")

        self.gridLayout_9.addWidget(self.label_45, 1, 0, 1, 1)

        self.label_49 = QLabel(self.groupBox_14)
        self.label_49.setObjectName(u"label_49")

        self.gridLayout_9.addWidget(self.label_49, 3, 0, 1, 1)

        self.label_43 = QLabel(self.groupBox_14)
        self.label_43.setObjectName(u"label_43")

        self.gridLayout_9.addWidget(self.label_43, 0, 0, 1, 1)

        self.stat_processing_queue = QLabel(self.groupBox_14)
        self.stat_processing_queue.setObjectName(u"stat_processing_queue")

        self.gridLayout_9.addWidget(self.stat_processing_queue, 1, 1, 1, 1)

        self.label_44 = QLabel(self.groupBox_14)
        self.label_44.setObjectName(u"label_44")

        self.gridLayout_9.addWidget(self.label_44, 2, 0, 1, 1)

        self.stat_hub_queue = QLabel(self.groupBox_14)
        self.stat_hub_queue.setObjectName(u"stat_hub_queue")

        self.gridLayout_9.addWidget(self.stat_hub_queue, 2, 1, 1, 1)

        self.stat_app_queue = QLabel(self.groupBox_14)
        self.stat_app_queue.setObjectName(u"stat_app_queue")

        self.gridLayout_9.addWidget(self.stat_app_queue, 3, 1, 1, 1)


        self.verticalLayout.addWidget(self.groupBox_14)

        self.verticalSpacer_2 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout.addItem(self.verticalSpacer_2)

        self.scrollArea_3.setWidget(self.scrollAreaWidgetContents_3)

        self.verticalLayout_10.addWidget(self.scrollArea_3)

        self.tabWidget.addTab(self.tab_4, "")
        self.splitter.addWidget(self.tabWidget)
        self.splitter_2.addWidget(self.splitter)
        self.output_logs = QTabWidget(self.splitter_2)
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
        self.splitter_2.addWidget(self.output_logs)

        self.verticalLayout_6.addWidget(self.splitter_2)

        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QMenuBar(MainWindow)
        self.menubar.setObjectName(u"menubar")
        self.menubar.setGeometry(QRect(0, 0, 736, 22))
        self.menuFile = QMenu(self.menubar)
        self.menuFile.setObjectName(u"menuFile")
        self.menuHelp = QMenu(self.menubar)
        self.menuHelp.setObjectName(u"menuHelp")
        self.menuPreferences = QMenu(self.menubar)
        self.menuPreferences.setObjectName(u"menuPreferences")
        self.menu_debug = QMenu(self.menubar)
        self.menu_debug.setObjectName(u"menu_debug")
        self.menu_debug_tracking = QMenu(self.menu_debug)
        self.menu_debug_tracking.setObjectName(u"menu_debug_tracking")
        self.menu_debug_exception = QMenu(self.menu_debug)
        self.menu_debug_exception.setObjectName(u"menu_debug_exception")
        self.tray_context_menu = QMenu(self.menubar)
        self.tray_context_menu.setObjectName(u"tray_context_menu")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QStatusBar(MainWindow)
        self.statusbar.setObjectName(u"statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.menubar.addAction(self.menuFile.menuAction())
        self.menubar.addAction(self.menuPreferences.menuAction())
        self.menubar.addAction(self.menuHelp.menuAction())
        self.menubar.addAction(self.menu_debug.menuAction())
        self.menubar.addAction(self.tray_context_menu.menuAction())
        self.menuFile.addAction(self.file_tracking_start)
        self.menuFile.addAction(self.file_tracking_pause)
        self.menuFile.addSeparator()
        self.menuFile.addAction(self.file_save)
        self.menuFile.addAction(self.actionImport)
        self.menuFile.addAction(self.actionExport)
        self.menuFile.addSeparator()
        self.menuFile.addAction(self.actionRestart)
        self.menuFile.addAction(self.menu_exit)
        self.menuHelp.addAction(self.actionDocumentation)
        self.menuHelp.addAction(self.actionAbout)
        self.menuHelp.addSeparator()
        self.menuHelp.addAction(self.actionWebsite)
        self.menuHelp.addAction(self.actionReddit)
        self.menuHelp.addAction(self.actionFacebook)
        self.menuPreferences.addAction(self.menu_allow_minimise)
        self.menuPreferences.addAction(self.actionShow_Log)
        self.menu_debug.addAction(self.menu_debug_tracking.menuAction())
        self.menu_debug.addAction(self.menu_debug_exception.menuAction())
        self.menu_debug_tracking.addAction(self.debug_tracking_start)
        self.menu_debug_tracking.addAction(self.debug_tracking_pause)
        self.menu_debug_tracking.addAction(self.debug_tracking_stop)
        self.menu_debug_exception.addAction(self.debug_raise_tracking)
        self.menu_debug_exception.addAction(self.debug_raise_processing)
        self.menu_debug_exception.addAction(self.debug_raise_hub)
        self.menu_debug_exception.addAction(self.debug_raise_gui)
        self.menu_debug_exception.addAction(self.debug_raise_app)
        self.tray_context_menu.addAction(self.tray_show)
        self.tray_context_menu.addAction(self.tray_hide)
        self.tray_context_menu.addSeparator()
        self.tray_context_menu.addAction(self.tray_exit)

        self.retranslateUi(MainWindow)
        self.render_samples.valueChanged.connect(self.label_2.setNum)
        self.save.clicked.connect(self.file_save.trigger)

        self.tabWidget.setCurrentIndex(0)
        self.output_logs.setCurrentIndex(1)


        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"MouseTracks", None))
        self.actionShow_Log.setText(QCoreApplication.translate("MainWindow", u"Display Output Log", None))
        self.file_save.setText(QCoreApplication.translate("MainWindow", u"Save", None))
#if QT_CONFIG(shortcut)
        self.file_save.setShortcut(QCoreApplication.translate("MainWindow", u"Ctrl+S", None))
#endif // QT_CONFIG(shortcut)
        self.actionExport.setText(QCoreApplication.translate("MainWindow", u"Export", None))
        self.actionImport.setText(QCoreApplication.translate("MainWindow", u"Import", None))
        self.actionAbout.setText(QCoreApplication.translate("MainWindow", u"About", None))
        self.actionDocumentation.setText(QCoreApplication.translate("MainWindow", u"Documentation", None))
        self.menu_exit.setText(QCoreApplication.translate("MainWindow", u"Exit", None))
        self.menu_allow_minimise.setText(QCoreApplication.translate("MainWindow", u"Minimise to Tray", None))
        self.file_tracking_start.setText(QCoreApplication.translate("MainWindow", u"Start", None))
        self.file_tracking_pause.setText(QCoreApplication.translate("MainWindow", u"Pause", None))
        self.debug_tracking_start.setText(QCoreApplication.translate("MainWindow", u"Start", None))
        self.debug_tracking_pause.setText(QCoreApplication.translate("MainWindow", u"Pause", None))
        self.debug_tracking_stop.setText(QCoreApplication.translate("MainWindow", u"Stop", None))
        self.debug_raise_tracking.setText(QCoreApplication.translate("MainWindow", u"Tracking", None))
        self.debug_raise_processing.setText(QCoreApplication.translate("MainWindow", u"Processing", None))
        self.debug_raise_hub.setText(QCoreApplication.translate("MainWindow", u"Hub", None))
        self.debug_raise_gui.setText(QCoreApplication.translate("MainWindow", u"GUI", None))
        self.debug_raise_app.setText(QCoreApplication.translate("MainWindow", u"App Detection", None))
        self.actionRestart.setText(QCoreApplication.translate("MainWindow", u"Restart", None))
        self.actionSave_Image.setText(QCoreApplication.translate("MainWindow", u"Save Image", None))
        self.actionVisit_Website.setText(QCoreApplication.translate("MainWindow", u"Visit Website", None))
        self.actionVisit_Reddit.setText(QCoreApplication.translate("MainWindow", u"Reddit", None))
        self.actionVisit_Facebook.setText(QCoreApplication.translate("MainWindow", u"Facebook", None))
        self.actionWebsite.setText(QCoreApplication.translate("MainWindow", u"Website", None))
        self.actionReddit.setText(QCoreApplication.translate("MainWindow", u"Reddit", None))
        self.actionFacebook.setText(QCoreApplication.translate("MainWindow", u"Facebook", None))
        self.tray_exit.setText(QCoreApplication.translate("MainWindow", u"Exit", None))
        self.tray_show.setText(QCoreApplication.translate("MainWindow", u"Open", None))
        self.tray_hide.setText(QCoreApplication.translate("MainWindow", u"Minimise to Tray", None))
        self.thumbnail.setText(QCoreApplication.translate("MainWindow", u"<image>", None))
        self.save_render.setText(QCoreApplication.translate("MainWindow", u"Save Render", None))
        self.groupBox_2.setTitle(QCoreApplication.translate("MainWindow", u"Profile Selection", None))
        self.current_profile.setItemText(0, QCoreApplication.translate("MainWindow", u"*Main", None))
        self.current_profile.setItemText(1, QCoreApplication.translate("MainWindow", u"*Path of Exile", None))
        self.current_profile.setItemText(2, QCoreApplication.translate("MainWindow", u"Overwatch", None))

        self.auto_switch_profile.setText(QCoreApplication.translate("MainWindow", u"Keep currently loaded selected", None))
        self.groupBox_3.setTitle(QCoreApplication.translate("MainWindow", u"Map Type", None))
        self.groupBox_4.setTitle(QCoreApplication.translate("MainWindow", u"Colour Options", None))
        self.colour_option.setItemText(0, QCoreApplication.translate("MainWindow", u"Default", None))
        self.colour_option.setItemText(1, QCoreApplication.translate("MainWindow", u"Citrus", None))
        self.colour_option.setItemText(2, QCoreApplication.translate("MainWindow", u"Sunburst", None))

        self.groupBox_9.setTitle(QCoreApplication.translate("MainWindow", u"Stats", None))
        self.label_8.setText(QCoreApplication.translate("MainWindow", u"Total Upload:", None))
        self.stat_download_total.setText(QCoreApplication.translate("MainWindow", u"1.32 TB", None))
        self.stat_clicks.setText(QCoreApplication.translate("MainWindow", u"526462", None))
        self.label_21.setText(QCoreApplication.translate("MainWindow", u"Mouse Clicks:", None))
        self.label_22.setText(QCoreApplication.translate("MainWindow", u"Active Time:", None))
        self.label_23.setText(QCoreApplication.translate("MainWindow", u"Inactive Time:", None))
        self.label_19.setText(QCoreApplication.translate("MainWindow", u"Cursor Distance:", None))
        self.label.setText(QCoreApplication.translate("MainWindow", u"Gamepad Buttons Pressed:", None))
        self.stat_active.setText(QCoreApplication.translate("MainWindow", u"45.0 hours", None))
        self.stat_keys.setText(QCoreApplication.translate("MainWindow", u"42544", None))
        self.label_20.setText(QCoreApplication.translate("MainWindow", u"Keys Pressed:", None))
        self.label_9.setText(QCoreApplication.translate("MainWindow", u"Mouse Scrolls:", None))
        self.stat_buttons.setText(QCoreApplication.translate("MainWindow", u"264", None))
        self.stat_inactive.setText(QCoreApplication.translate("MainWindow", u"5.30 hours", None))
        self.label_4.setText(QCoreApplication.translate("MainWindow", u"Total Download:", None))
        self.stat_scroll.setText(QCoreApplication.translate("MainWindow", u"316177", None))
        self.stat_distance.setText(QCoreApplication.translate("MainWindow", u"32.54km", None))
        self.stat_upload_total.setText(QCoreApplication.translate("MainWindow", u"643.16 MB", None))
        self.label_11.setText(QCoreApplication.translate("MainWindow", u"Elapsed Time:", None))
        self.stat_elapsed.setText(QCoreApplication.translate("MainWindow", u"50.30 hours", None))
        self.tracking_start.setText(QCoreApplication.translate("MainWindow", u"Start / Unpause", None))
        self.tracking_pause.setText(QCoreApplication.translate("MainWindow", u"Pause", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab), QCoreApplication.translate("MainWindow", u"Main", None))
        self.custom_resolution.setTitle(QCoreApplication.translate("MainWindow", u"Custom Render Resolution", None))
        self.groupBox_5.setTitle(QCoreApplication.translate("MainWindow", u"Render Sampling", None))
        self.label_2.setText(QCoreApplication.translate("MainWindow", u"4", None))
        self.record_history.setTitle(QCoreApplication.translate("MainWindow", u"History", None))
        self.label_7.setText(QCoreApplication.translate("MainWindow", u"Number of hours to keep available", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_3), QCoreApplication.translate("MainWindow", u"Advanced", None))
        self.groupBox_11.setTitle(QCoreApplication.translate("MainWindow", u"Current Application", None))
        self.label_6.setText(QCoreApplication.translate("MainWindow", u"Tracked", None))
        self.label_10.setText(QCoreApplication.translate("MainWindow", u"Window Name", None))
        self.label_5.setText(QCoreApplication.translate("MainWindow", u"Executable", None))
        self.stat_app_exe.setText(QCoreApplication.translate("MainWindow", u"designer.exe", None))
        self.stat_app_window_name.setText(QCoreApplication.translate("MainWindow", u"Qt Widgets Designer", None))
        self.stat_app_tracked.setText(QCoreApplication.translate("MainWindow", u"No", None))
        self.groupBox_10.setTitle(QCoreApplication.translate("MainWindow", u"Time Since", None))
        self.save.setText(QCoreApplication.translate("MainWindow", u"Save", None))
        self.pushButton.setText(QCoreApplication.translate("MainWindow", u"AppList.txt Reload", None))
        self.thumbnail_refresh.setText(QCoreApplication.translate("MainWindow", u"Thumbnail Update", None))
        self.time_since_thumbnail.setText(QCoreApplication.translate("MainWindow", u"5.4 s", None))
        self.label_3.setText(QCoreApplication.translate("MainWindow", u"4m12s", None))
        self.time_since_save.setText(QCoreApplication.translate("MainWindow", u"23.5 s", None))
        self.groupBox_13.setTitle(QCoreApplication.translate("MainWindow", u"Components", None))
        self.stat_tracking_state.setText(QCoreApplication.translate("MainWindow", u"Running", None))
        self.label_34.setText(QCoreApplication.translate("MainWindow", u"Tracking", None))
        self.label_36.setText(QCoreApplication.translate("MainWindow", u"Hub", None))
        self.label_39.setText(QCoreApplication.translate("MainWindow", u"Processing", None))
        self.stat_app_state.setText(QCoreApplication.translate("MainWindow", u"Running", None))
        self.stat_hub_state.setText(QCoreApplication.translate("MainWindow", u"Running", None))
        self.stat_processing_state.setText(QCoreApplication.translate("MainWindow", u"Running", None))
        self.label_40.setText(QCoreApplication.translate("MainWindow", u"Application Detection", None))
        self.groupBox_14.setTitle(QCoreApplication.translate("MainWindow", u"Queue Size", None))
        self.stat_tracking_queue.setText(QCoreApplication.translate("MainWindow", u"0", None))
        self.label_45.setText(QCoreApplication.translate("MainWindow", u"Processing", None))
        self.label_49.setText(QCoreApplication.translate("MainWindow", u"Application Detection", None))
        self.label_43.setText(QCoreApplication.translate("MainWindow", u"Tracking", None))
        self.stat_processing_queue.setText(QCoreApplication.translate("MainWindow", u"12", None))
        self.label_44.setText(QCoreApplication.translate("MainWindow", u"Hub", None))
        self.stat_hub_queue.setText(QCoreApplication.translate("MainWindow", u"0", None))
        self.stat_app_queue.setText(QCoreApplication.translate("MainWindow", u"0", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_4), QCoreApplication.translate("MainWindow", u"Status", None))

        __sortingEnabled = self.listWidget_3.isSortingEnabled()
        self.listWidget_3.setSortingEnabled(False)
        ___qlistwidgetitem = self.listWidget_3.item(0)
        ___qlistwidgetitem.setText(QCoreApplication.translate("MainWindow", u"[11:05:38] Left mouse button being held at (1480, 730).", None));
        ___qlistwidgetitem1 = self.listWidget_3.item(1)
        ___qlistwidgetitem1.setText(QCoreApplication.translate("MainWindow", u"[11:05:38] Left mouse button being held at (1454, 658).", None));
        ___qlistwidgetitem2 = self.listWidget_3.item(2)
        ___qlistwidgetitem2.setText(QCoreApplication.translate("MainWindow", u"[11:05:38] Left mouse button being held at (1447, 639).", None));
        ___qlistwidgetitem3 = self.listWidget_3.item(3)
        ___qlistwidgetitem3.setText(QCoreApplication.translate("MainWindow", u"[11:05:38] Left mouse button being held at (1447, 639).", None));
        ___qlistwidgetitem4 = self.listWidget_3.item(4)
        ___qlistwidgetitem4.setText(QCoreApplication.translate("MainWindow", u"[11:05:40] Left mouse button clicked at (1448, 835).", None));
        ___qlistwidgetitem5 = self.listWidget_3.item(5)
        ___qlistwidgetitem5.setText(QCoreApplication.translate("MainWindow", u"[11:05:40] Left mouse button being held at (1427, 740).", None));
        ___qlistwidgetitem6 = self.listWidget_3.item(6)
        ___qlistwidgetitem6.setText(QCoreApplication.translate("MainWindow", u"[11:05:40] Left mouse button being held at (1424, 660).", None));
        ___qlistwidgetitem7 = self.listWidget_3.item(7)
        ___qlistwidgetitem7.setText(QCoreApplication.translate("MainWindow", u"[11:05:40] Left mouse button being held at (1425, 643).", None));
        ___qlistwidgetitem8 = self.listWidget_3.item(8)
        ___qlistwidgetitem8.setText(QCoreApplication.translate("MainWindow", u"[11:05:41] Left mouse button being held at (1425, 643).", None));
        ___qlistwidgetitem9 = self.listWidget_3.item(9)
        ___qlistwidgetitem9.setText(QCoreApplication.translate("MainWindow", u"[11:05:41] Finished loading data. | 170 commands queued for processing.", None));
        ___qlistwidgetitem10 = self.listWidget_3.item(10)
        ___qlistwidgetitem10.setText(QCoreApplication.translate("MainWindow", u"[11:05:43] Left mouse button clicked at (1109, 705).", None));
        ___qlistwidgetitem11 = self.listWidget_3.item(11)
        ___qlistwidgetitem11.setText(QCoreApplication.translate("MainWindow", u"[11:05:44] Application gained focus: Qt Designer | Application resolution is 2576x1416.", None));
        ___qlistwidgetitem12 = self.listWidget_3.item(12)
        ___qlistwidgetitem12.setText(QCoreApplication.translate("MainWindow", u"[11:05:44] Switching profile to Qt Designer. | Preparing data to save...", None));
        ___qlistwidgetitem13 = self.listWidget_3.item(13)
        ___qlistwidgetitem13.setText(QCoreApplication.translate("MainWindow", u"[11:05:44] Left mouse button clicked at (1493, 996).", None));
        ___qlistwidgetitem14 = self.listWidget_3.item(14)
        ___qlistwidgetitem14.setText(QCoreApplication.translate("MainWindow", u"[11:05:45] Left mouse button clicked at (1506, 1024).", None));
        ___qlistwidgetitem15 = self.listWidget_3.item(15)
        ___qlistwidgetitem15.setText(QCoreApplication.translate("MainWindow", u"[11:05:51] Left mouse button clicked at (781, 412).", None));
        ___qlistwidgetitem16 = self.listWidget_3.item(16)
        ___qlistwidgetitem16.setText(QCoreApplication.translate("MainWindow", u"[11:05:55] Left mouse button clicked at (2128, 162).", None));
        ___qlistwidgetitem17 = self.listWidget_3.item(17)
        ___qlistwidgetitem17.setText(QCoreApplication.translate("MainWindow", u"[11:05:56] 348 commands queued for processing.", None));
        ___qlistwidgetitem18 = self.listWidget_3.item(18)
        ___qlistwidgetitem18.setText(QCoreApplication.translate("MainWindow", u"[11:06:02] Left mouse button clicked at (89, 535).", None));
        self.listWidget_3.setSortingEnabled(__sortingEnabled)

        self.output_logs.setTabText(self.output_logs.indexOf(self.tab_6), QCoreApplication.translate("MainWindow", u"Tracking", None))
        self.output_logs.setTabText(self.output_logs.indexOf(self.tab_7), QCoreApplication.translate("MainWindow", u"Processing", None))
        self.menuFile.setTitle(QCoreApplication.translate("MainWindow", u"File", None))
        self.menuHelp.setTitle(QCoreApplication.translate("MainWindow", u"Help", None))
        self.menuPreferences.setTitle(QCoreApplication.translate("MainWindow", u"Preferences", None))
        self.menu_debug.setTitle(QCoreApplication.translate("MainWindow", u"Debug", None))
        self.menu_debug_tracking.setTitle(QCoreApplication.translate("MainWindow", u"Set Tracking State", None))
        self.menu_debug_exception.setTitle(QCoreApplication.translate("MainWindow", u"Raise Exception", None))
        self.tray_context_menu.setTitle(QCoreApplication.translate("MainWindow", u"_Tray_", None))
    # retranslateUi

