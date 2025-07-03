# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'applist.ui'
##
## Created by: Qt User Interface Compiler version 6.8.0
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QGroupBox,
    QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QPushButton, QRadioButton, QSizePolicy,
    QSpacerItem, QSplitter, QVBoxLayout, QWidget)

class Ui_Form(object):
    def setupUi(self, Form):
        if not Form.objectName():
            Form.setObjectName(u"Form")
        Form.resize(866, 669)
        self.verticalLayout = QVBoxLayout(Form)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.splitter = QSplitter(Form)
        self.splitter.setObjectName(u"splitter")
        self.splitter.setOrientation(Qt.Orientation.Horizontal)
        self.layoutWidget = QWidget(self.splitter)
        self.layoutWidget.setObjectName(u"layoutWidget")
        self.verticalLayout_2 = QVBoxLayout(self.layoutWidget)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.verticalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.label_5 = QLabel(self.layoutWidget)
        self.label_5.setObjectName(u"label_5")
        self.label_5.setWordWrap(True)

        self.verticalLayout_2.addWidget(self.label_5)

        self.groupBox_3 = QGroupBox(self.layoutWidget)
        self.groupBox_3.setObjectName(u"groupBox_3")
        self.verticalLayout_3 = QVBoxLayout(self.groupBox_3)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.executable = QComboBox(self.groupBox_3)
        self.executable.setObjectName(u"executable")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.executable.sizePolicy().hasHeightForWidth())
        self.executable.setSizePolicy(sizePolicy)
        self.executable.setEditable(True)

        self.horizontalLayout.addWidget(self.executable)

        self.browse = QPushButton(self.groupBox_3)
        self.browse.setObjectName(u"browse")

        self.horizontalLayout.addWidget(self.browse)


        self.verticalLayout_3.addLayout(self.horizontalLayout)

        self.label_6 = QLabel(self.groupBox_3)
        self.label_6.setObjectName(u"label_6")
        self.label_6.setWordWrap(True)

        self.verticalLayout_3.addWidget(self.label_6)


        self.verticalLayout_2.addWidget(self.groupBox_3)

        self.groupBox_6 = QGroupBox(self.layoutWidget)
        self.groupBox_6.setObjectName(u"groupBox_6")
        self.verticalLayout_6 = QVBoxLayout(self.groupBox_6)
        self.verticalLayout_6.setObjectName(u"verticalLayout_6")
        self.profile_name = QLineEdit(self.groupBox_6)
        self.profile_name.setObjectName(u"profile_name")

        self.verticalLayout_6.addWidget(self.profile_name)

        self.label_10 = QLabel(self.groupBox_6)
        self.label_10.setObjectName(u"label_10")
        self.label_10.setMinimumSize(QSize(70, 0))
        self.label_10.setWordWrap(True)

        self.verticalLayout_6.addWidget(self.label_10)


        self.verticalLayout_2.addWidget(self.groupBox_6)

        self.window_title_enabled = QGroupBox(self.layoutWidget)
        self.window_title_enabled.setObjectName(u"window_title_enabled")
        self.window_title_enabled.setCheckable(True)
        self.window_title_enabled.setChecked(False)
        self.verticalLayout_4 = QVBoxLayout(self.window_title_enabled)
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.label_8 = QLabel(self.window_title_enabled)
        self.label_8.setObjectName(u"label_8")

        self.verticalLayout_4.addWidget(self.label_8)

        self.window_title = QLineEdit(self.window_title_enabled)
        self.window_title.setObjectName(u"window_title")

        self.verticalLayout_4.addWidget(self.window_title)

        self.label = QLabel(self.window_title_enabled)
        self.label.setObjectName(u"label")
        self.label.setWordWrap(True)

        self.verticalLayout_4.addWidget(self.label)


        self.verticalLayout_2.addWidget(self.window_title_enabled)

        self.groupBox_5 = QGroupBox(self.layoutWidget)
        self.groupBox_5.setObjectName(u"groupBox_5")
        self.verticalLayout_5 = QVBoxLayout(self.groupBox_5)
        self.verticalLayout_5.setObjectName(u"verticalLayout_5")
        self.label_9 = QLabel(self.groupBox_5)
        self.label_9.setObjectName(u"label_9")

        self.verticalLayout_5.addWidget(self.label_9)

        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.state_enabled = QRadioButton(self.groupBox_5)
        self.state_enabled.setObjectName(u"state_enabled")
        self.state_enabled.setChecked(True)

        self.horizontalLayout_3.addWidget(self.state_enabled)

        self.state_ignored = QRadioButton(self.groupBox_5)
        self.state_ignored.setObjectName(u"state_ignored")

        self.horizontalLayout_3.addWidget(self.state_ignored)

        self.state_disabled = QRadioButton(self.groupBox_5)
        self.state_disabled.setObjectName(u"state_disabled")

        self.horizontalLayout_3.addWidget(self.state_disabled)


        self.verticalLayout_5.addLayout(self.horizontalLayout_3)

        self.label_2 = QLabel(self.groupBox_5)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setWordWrap(True)

        self.verticalLayout_5.addWidget(self.label_2)


        self.verticalLayout_2.addWidget(self.groupBox_5)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_2.addItem(self.verticalSpacer)

        self.horizontalLayout_5 = QHBoxLayout()
        self.horizontalLayout_5.setObjectName(u"horizontalLayout_5")
        self.create = QPushButton(self.layoutWidget)
        self.create.setObjectName(u"create")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Fixed)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.create.sizePolicy().hasHeightForWidth())
        self.create.setSizePolicy(sizePolicy1)

        self.horizontalLayout_5.addWidget(self.create)

        self.advanced = QCheckBox(self.layoutWidget)
        self.advanced.setObjectName(u"advanced")
        self.advanced.setChecked(True)

        self.horizontalLayout_5.addWidget(self.advanced)


        self.verticalLayout_2.addLayout(self.horizontalLayout_5)

        self.splitter.addWidget(self.layoutWidget)
        self.layoutWidget1 = QWidget(self.splitter)
        self.layoutWidget1.setObjectName(u"layoutWidget1")
        self.verticalLayout_8 = QVBoxLayout(self.layoutWidget1)
        self.verticalLayout_8.setObjectName(u"verticalLayout_8")
        self.verticalLayout_8.setContentsMargins(0, 0, 0, 0)
        self.open = QPushButton(self.layoutWidget1)
        self.open.setObjectName(u"open")

        self.verticalLayout_8.addWidget(self.open)

        self.label_3 = QLabel(self.layoutWidget1)
        self.label_3.setObjectName(u"label_3")
        self.label_3.setWordWrap(True)

        self.verticalLayout_8.addWidget(self.label_3)

        self.label_4 = QLabel(self.layoutWidget1)
        self.label_4.setObjectName(u"label_4")
        self.label_4.setWordWrap(True)

        self.verticalLayout_8.addWidget(self.label_4)

        self.rules = QListWidget(self.layoutWidget1)
        QListWidgetItem(self.rules)
        QListWidgetItem(self.rules)
        self.rules.setObjectName(u"rules")
        self.rules.setBaseSize(QSize(100, 0))

        self.verticalLayout_8.addWidget(self.rules)

        self.remove = QPushButton(self.layoutWidget1)
        self.remove.setObjectName(u"remove")

        self.verticalLayout_8.addWidget(self.remove)

        self.splitter.addWidget(self.layoutWidget1)

        self.verticalLayout.addWidget(self.splitter)

        self.save = QPushButton(Form)
        self.save.setObjectName(u"save")

        self.verticalLayout.addWidget(self.save)


        self.retranslateUi(Form)
        self.advanced.toggled.connect(self.label_6.setVisible)
        self.advanced.toggled.connect(self.window_title_enabled.setVisible)
        self.advanced.toggled.connect(self.groupBox_5.setVisible)
        self.state_enabled.toggled.connect(self.groupBox_6.setEnabled)
        self.advanced.toggled.connect(self.open.setVisible)

        QMetaObject.connectSlotsByName(Form)
    # setupUi

    def retranslateUi(self, Form):
        Form.setWindowTitle(QCoreApplication.translate("Form", u"AppList Updater", None))
        self.label_5.setText(QCoreApplication.translate("Form", u"Add or update the tracking information for a profile.\n"
"A profile will activate once the linked application gains focus.", None))
#if QT_CONFIG(tooltip)
        self.groupBox_3.setToolTip(QCoreApplication.translate("Form", u"Select an executable name from the loaded applications, or type one.\n"
"It is case sensitive and supports partial paths.\n"
"The <*> marker is treated as a wildcard, and multiple can be used.\n"
"\n"
"Examples:\n"
"- MyGame.exe\n"
"- MyGame_build_<*>.exe\n"
"- steamapps/MyGame/bin/MyGame.exe\n"
"- \\mygame\\MyGame.exe", None))
#endif // QT_CONFIG(tooltip)
        self.groupBox_3.setTitle(QCoreApplication.translate("Form", u"Executable", None))
        self.executable.setCurrentText(QCoreApplication.translate("Form", u"Game_Win64.exe", None))
        self.browse.setText(QCoreApplication.translate("Form", u"Search", None))
        self.label_6.setText(QCoreApplication.translate("Form", u"- Case sensitive<br>- The wildcard character sequence <strong><code>&#60;*&#62;</code></strong> is supported.<br>- Partial paths are supported for a narrower search scope.", None))
#if QT_CONFIG(tooltip)
        self.groupBox_6.setToolTip(QCoreApplication.translate("Form", u"Set the name of the profile.\n"
"Multiple rules can write to the same profile.\n"
"\n"
"If this field is left empty, the profile name will be automatically determined. \n"
"It will first try to use the 'Window Title' (if one is specified for this rule). \n"
"If no 'Window Title' is specified, it will use the 'Executable' name as the profile name.", None))
#endif // QT_CONFIG(tooltip)
        self.groupBox_6.setTitle(QCoreApplication.translate("Form", u"Profile Name", None))
        self.profile_name.setPlaceholderText(QCoreApplication.translate("Form", u"Game_Win64", None))
        self.label_10.setText(QCoreApplication.translate("Form", u"- Multiple rules can point to the same profile.\n"
"- If not set, name defaults to Window Title (if specified), otherwise Executable.", None))
#if QT_CONFIG(tooltip)
        self.window_title_enabled.setToolTip(QCoreApplication.translate("Form", u"Add a check on the window title.\n"
"These rules take priority over any matching rule without a window title.\n"
"This may be used for example to ignore a splash screen when an application is\n"
"being loaded, assuming the splash screen has a different title.", None))
#endif // QT_CONFIG(tooltip)
        self.window_title_enabled.setTitle(QCoreApplication.translate("Form", u"Window Title", None))
        self.label_8.setText(QCoreApplication.translate("Form", u"Only trigger the profile when this window title is matched.", None))
        self.label.setText(QCoreApplication.translate("Form", u"- The wildcard character sequence <strong><code>&#60;*&#62;</code></strong> is supported.", None))
#if QT_CONFIG(tooltip)
        self.groupBox_5.setToolTip(QCoreApplication.translate("Form", u"Set how the profile should work.\n"
"\n"
"- An ignored profile is meant to work in conjunction with the window title option,\n"
"so particular cases such as splash screens can be ignored instead of recording low\n"
"resolution data to the application.\n"
"\n"
"- A disabled profile is for when the tracking data should be discarded. As of right\n"
"now it records to a \"Untracked\" profile.", None))
#endif // QT_CONFIG(tooltip)
        self.groupBox_5.setTitle(QCoreApplication.translate("Form", u"State", None))
        self.label_9.setText(QCoreApplication.translate("Form", u"Set how the profile behaves.", None))
        self.state_enabled.setText(QCoreApplication.translate("Form", u"Enabled", None))
        self.state_ignored.setText(QCoreApplication.translate("Form", u"Ignored", None))
        self.state_disabled.setText(QCoreApplication.translate("Form", u"Disabled", None))
        self.label_2.setText(QCoreApplication.translate("Form", u"- Enabled: Track this profile.\n"
"- Ignored: Use in conjunction with the window title to prevent the profile changing for certain windows (eg. splash screens).\n"
"- Disabled: Stop recording all data while profile is loaded.", None))
#if QT_CONFIG(tooltip)
        self.create.setToolTip(QCoreApplication.translate("Form", u"Create the new rule or update the matching one.", None))
#endif // QT_CONFIG(tooltip)
        self.create.setText(QCoreApplication.translate("Form", u"Create / Update Rule", None))
#if QT_CONFIG(tooltip)
        self.advanced.setToolTip(QCoreApplication.translate("Form", u"Show advanced options.", None))
#endif // QT_CONFIG(tooltip)
        self.advanced.setText(QCoreApplication.translate("Form", u"Advanced", None))
#if QT_CONFIG(tooltip)
        self.open.setToolTip(QCoreApplication.translate("Form", u"Open the AppList.txt file.", None))
#endif // QT_CONFIG(tooltip)
        self.open.setText(QCoreApplication.translate("Form", u"Open AppList.txt", None))
        self.label_3.setText(QCoreApplication.translate("Form", u"Listed below are all matching profile rules for the currently selected executable.", None))
        self.label_4.setText(QCoreApplication.translate("Form", u"The format is as follows:\n"
" - Executable.exe: Profile Name\n"
" - Executable.exe[Window Title]: Profile Name", None))

        __sortingEnabled = self.rules.isSortingEnabled()
        self.rules.setSortingEnabled(False)
        ___qlistwidgetitem = self.rules.item(0)
        ___qlistwidgetitem.setText(QCoreApplication.translate("Form", u"Game_Win64.exe: My Game", None));
        ___qlistwidgetitem1 = self.rules.item(1)
        ___qlistwidgetitem1.setText(QCoreApplication.translate("Form", u"Game_Win64.exe[Title]: <ignore>", None));
        self.rules.setSortingEnabled(__sortingEnabled)

#if QT_CONFIG(tooltip)
        self.rules.setToolTip(QCoreApplication.translate("Form", u"List of matching rules.\n"
"\n"
"Possible formats:\n"
"- App.exe\n"
"- App.exe[Title]\n"
"- App.exe: Name\n"
"- App.exe[Title]: Name", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(tooltip)
        self.remove.setToolTip(QCoreApplication.translate("Form", u"Remove the selected rule.", None))
#endif // QT_CONFIG(tooltip)
        self.remove.setText(QCoreApplication.translate("Form", u"Remove Rule", None))
#if QT_CONFIG(tooltip)
        self.save.setToolTip(QCoreApplication.translate("Form", u"Save all changes made and close this window.", None))
#endif // QT_CONFIG(tooltip)
        self.save.setText(QCoreApplication.translate("Form", u"Save Changes and Exit", None))
    # retranslateUi

