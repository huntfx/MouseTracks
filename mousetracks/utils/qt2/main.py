from __future__ import absolute_import

from contextlib import contextmanager

from .Qt import QtWidgets, QtCore


def layoutToWidget(layout):
    """Return a widget or convert a layout to a widget."""
    if isinstance(layout, QtBase):
        layout = layout.QObject
    if isinstance(layout, QtWidgets.QLayout):
        new = QtWidgets.QWidget()
        new.setLayout(layout)
        return new
    return layout


class QtBase(object):
    def __init__(self, func, parent=None, *args, **kwargs):
        if isinstance(func, QtBase):
            print('QtCustom.{}()'.format(func.__class__.__name__))
            self.QObject = func.QObject
        else:
            print('{}()'.format(func.__class__.__name__))
            self.QObject = func

    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        pass


class QtLayout(QtBase):
    def __init__(self, func, parent=None, *args, **kwargs):
        super(QtLayout, self).__init__(func, parent, *args, **kwargs)

        if parent is not None:
            if isinstance(parent, QtWidgets.QMainWindow):
                print('{}.setCentralWidget(layoutToWidget({}))'.format(parent.__class__.__name__, self.QObject.__class__.__name__))
                parent.setCentralWidget(layoutToWidget(self.QObject))

    @contextmanager
    def addLayout(self, layout, *args, **kwargs):
        with QtLayout(layout, parent=self, *args, **kwargs) as layout:
            self.QObject.addLayout(layout.QObject)
            print('{}.addLayout({})'.format(self.QObject.__class__.__name__, layout.QObject.__class__.__name__))
            yield layout

    def addWidget(self, widget, *args, **kwargs):
        with QtWidget(widget, None, *args, **kwargs) as widget:
            self.QObject.addWidget(widget.QObject)
            print('{}.addWidget({})'.format(self.QObject.__class__.__name__, widget.QObject.__class__.__name__))
            return widget


class QtWidget(QtBase):
    def __init__(self, func, parent=None, *args, **kwargs):
        super(QtWidget, self).__init__(func, parent, *args, **kwargs)

        if parent is not None:
            if isinstance(parent, QtWidgets.QMainWindow):
                parent.setCentralWidget(self.QObject)

class QCheckBox(QtWidget):
    def __init__(self, *args, **kwargs):
        super(QCheckBox, self).__init__(QtWidgets.QCheckBox(*args, **kwargs))