# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'about.ui'
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
from PySide6.QtWidgets import (QApplication, QDialog, QHBoxLayout, QLabel,
    QPushButton, QSizePolicy, QSpacerItem, QVBoxLayout,
    QWidget)

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        if not Dialog.objectName():
            Dialog.setObjectName(u"Dialog")
        Dialog.resize(260, 200)
        Dialog.setMinimumSize(QSize(260, 200))
        Dialog.setMaximumSize(QSize(260, 200))
        self.verticalLayout = QVBoxLayout(Dialog)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.icon = QLabel(Dialog)
        self.icon.setObjectName(u"icon")
        self.icon.setMinimumSize(QSize(64, 64))
        self.icon.setMaximumSize(QSize(64, 64))
        self.icon.setPixmap(QPixmap(u"resources/images/icon.png"))
        self.icon.setScaledContents(True)
        self.icon.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.horizontalLayout.addWidget(self.icon)


        self.verticalLayout.addLayout(self.horizontalLayout)

        self.label = QLabel(Dialog)
        self.label.setObjectName(u"label")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.verticalLayout.addWidget(self.label)

        self.version = QLabel(Dialog)
        self.version.setObjectName(u"version")
        self.version.setTextFormat(Qt.TextFormat.RichText)
        self.version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.version.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)

        self.verticalLayout.addWidget(self.version)

        self.latest = QLabel(Dialog)
        self.latest.setObjectName(u"latest")
        self.latest.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.verticalLayout.addWidget(self.latest)

        self.close = QPushButton(Dialog)
        self.close.setObjectName(u"close")

        self.verticalLayout.addWidget(self.close)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout.addItem(self.verticalSpacer)


        self.retranslateUi(Dialog)
        self.close.clicked.connect(Dialog.reject)

        QMetaObject.connectSlotsByName(Dialog)
    # setupUi

    def retranslateUi(self, Dialog):
        Dialog.setWindowTitle(QCoreApplication.translate("Dialog", u"About", None))
        self.icon.setText("")
        self.label.setText(QCoreApplication.translate("Dialog", u"<html><head/><body><p align=\"center\"><span style=\" font-size:14pt; font-weight:700;\">About MouseTracks</span></p></body></html>", None))
        self.version.setText(QCoreApplication.translate("Dialog", u"<span style=\" font-size:10pt;\">Version 2.0.0 (<a href=\"https://github.com/huntfx/MouseTracks/releases/tag/v2.0.0\">release notes</a>)</span>", None))
        self.latest.setText(QCoreApplication.translate("Dialog", u"You have the latest version.", None))
        self.latest.setProperty(u"text_update", QCoreApplication.translate("Dialog", u"An update is available.<br/><a href=\"https://github.com/huntfx/MouseTracks/releases/latest\">Click here</a> to visit the download page.", None))
        self.latest.setProperty(u"text_latest", QCoreApplication.translate("Dialog", u"You have the latest version.", None))
        self.latest.setProperty(u"text_install", QCoreApplication.translate("Dialog", u"A new version is ready to install.<br/>Restart to complete the installation.", None))
        self.close.setText(QCoreApplication.translate("Dialog", u"Close", None))
    # retranslateUi

