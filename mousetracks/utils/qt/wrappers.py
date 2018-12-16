"""This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""

from __future__ import absolute_import

from contextlib import contextmanager

from .Qt import QtWidgets, QtCore
from ..compatibility import callable, range, iteritems


_DATA = {
    'parent': None,
    'family': {},
}


class Parent(object):
    """Automatically handle the parent tree when creating the layouts.
    When building a GUI, "Parent.set(parent_window)" must be called first.
    """

    @staticmethod
    def set(parent, grandparent=None):
        """Set the current parent.
        Optionally provide the next parent so it can be queried later.
        """
        _DATA['parent'] = parent
        if grandparent is not None:
            Parent.update(parent, grandparent)

    @staticmethod
    def get(child=None):
        """Get the current parent or parent of the given child."""
        if child:
            return _DATA['family'][child]
        return _DATA['parent']

    @staticmethod
    def update(child, parent):
        _DATA['family'][child] = parent


class QtBase(QtCore.QObject):
    """Base wapper class.
    Contains methods used by both the layout and widgets.
    """
    def __init__(self, qt_object, *args, **kwargs):
        Parent.set(self, Parent.get())
        parent = self.parent()

        try:
            QtCore.QObject.__init__(self, parent)
        except KeyError:
            raise RuntimeError('the parent must first be set with Parent.set(parent)')

        if isinstance(parent, QtBase):
            parent._children.append(self)

        #Get information on the widget
        self._qt_data = {
            'object': qt_object,
            'created': not callable(qt_object),
            'type': qt_object if callable(qt_object) else qt_object.__class__,
            'args': args,
            'kwargs': kwargs
        }
        self._children = []
        self._children_data = {}

    def __enter__(self, inherit_funcs=[]):
        """Create the widget and inherit functions."""
        #Create the widget
        if self._qt_data['created']:
            self.QObject = self._qt_data['object']
        else:
            self.QObject = self._qt_data['object'](*self._qt_data['args'], **self._qt_data['kwargs'])
        
        #Inherit main funtions
        inherit_funcs += [
            'getContentsMargins',
            'addLayout',
            'addWidget',
            'setLayout',
            'setStyleSheet',
            'setObjectName',
            'setSizePolicy',
            'setToolTip',
        ]
        for func_name in inherit_funcs:
            if not hasattr(self, func_name):
                try:
                    func = getattr(self.QObject, func_name)
                    setattr(self, func_name, func)
                except AttributeError:
                    pass

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Set the current parent one generation upwards."""
        parent = self.parent()
        Parent.set(parent)
        return parent

    def parent(self):
        return Parent.get(self)

    def setParent(self, parent):
        """Set a new parent.
        I've forgotten why the commented out bit is needed,
        but leaving it here just in case
        """
        #old_parent = self.parent()
        Parent.update(self, parent)
        #if parent.parent() == old_parent:
        #    Parent.set(parent)

    def setContentsMargins(self, *args, **kwargs):
        """Set the contents margins.
        Supports a single number or 4 numbers, with optional overrides of
        "top", "left", "right" and "bottom".
        """
        margins = [None, None, None, None]
        #Set the base number first
        if args:
            num_args = len(args)
            if num_args == 1:
                margins = [args[0], args[0], args[0], args[0]]
            elif num_args == 4:
                margins = args
            else:
                raise TypeError('expect 1 or 4 arguments, got {}'.format(num_args))

        #Handle overrides
        if kwargs:
            for i, keyword in enumerate(['left', 'top', 'right', 'bottom']):
                if kwargs.get(keyword) is not None:
                    margins[i] = kwargs[keyword]

        #Set any remaining values
        if sum([i is not None for i in margins]) != 4:
            margins = [i if i is not None else j for i, j in zip(margins, self.getContentsMargins())]
        self.QObject.setContentsMargins(*margins)


class QtLayout(QtBase):
    """Wrapper for layout widgets."""
    def __init__(self, widget, *args, **kwargs):
        QtBase.__init__(self, widget, *args, **kwargs)
        self._converted = False

    def __enter__(self, inherit_funcs=[]):
        inherit_funcs += [
            'getContentsMargins',
            'setSpacing',
            'addStretch',
        ]
        QtBase.__enter__(self, inherit_funcs)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Add layout to parent layout.
        Some layouts can only take widgets,
        so we have to convert the class for some of them.
        """
        parent = QtBase.__exit__(self, exc_type, exc_val, exc_tb)
        
        #Convert QMainWindow to widget so layouts can be added
        if isinstance(parent, QtWidgets.QMainWindow):
            parent.setCentralWidget(self._convert_to_widget())
        
        #Handle QtLayout classes
        elif isinstance(parent, QtLayout):
            parent.addLayout(self.QObject)

        #Handle QtWidget classes
        elif isinstance(parent, QtWidget):
            if isinstance(parent, (WidgetTab, WidgetGroupBox)):
                parent.setLayout(self.QObject)
            elif isinstance(parent, WidgetScrollArea):
                parent.setWidget(self._convert_to_widget())
            else:
                parent.addWidget(self._convert_to_widget())

        #Handle any other base types
        else:
            parent.setLayout(self.QObject)

    def _convert_to_widget(self):
        """Convert the current layout to a widget."""
        if self._converted:
            return self.parent()

        #Get the parent to pass into the widget
        parent = self.parent()
        if isinstance(parent, QtBase):
            parent = parent.QObject
        
        #Wrap the current layout in a widget
        widget = QtWidgets.QWidget(parent)
        widget.setLayout(self.QObject)
        Parent.update(widget, parent)
        self.setParent(widget)
        self._converted = True
        return widget


class QtWidget(QtBase):
    """Wrapper for widgets."""
    def __init__(self, widget, *args, **kwargs):
        QtBase.__init__(self, widget, *args, **kwargs)

    def __enter__(self, inherit_funcs=[]):
        inherit_funcs += [
            'setVisible',
            'setEnabled'
            'setReadOnly',
            'setAlignment',
            'setMinimumWidth',
            'setMaximumWidth',
            'setMinimumHeight',
            'setMaximumHeight',
            'setFixedWidth',
            'setFixedHeight',
        ]
        QtBase.__enter__(self, inherit_funcs)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Add widget to parent layout."""
        parent = QtBase.__exit__(self, exc_type, exc_val, exc_tb)

        #Set widget if parent is a QMainWindow
        if isinstance(parent, QtWidgets.QMainWindow):
            parent.setCentralWidget(self.QObject)

        else:
            parent.addWidget(self.QObject)


class LayoutResizable(QtWidget):
    """Context manager for QSplitter."""
    def __init__(self, orientation, *args, **kwargs):
        QtWidget.__init__(self, QtWidgets.QSplitter, orientation, *args, **kwargs)


class LayoutResizableH(LayoutResizable):
    """Context manager for QSplitter set to horizontal."""
    def __init__(self, *args, **kwargs):
        LayoutResizable.__init__(self, QtCore.Qt.Horizontal, *args, **kwargs)


class LayoutResizableV(LayoutResizable):
    """Context manager for QSplitter set to vertical."""
    def __init__(self, *args, **kwargs):
        LayoutResizable.__init__(self, QtCore.Qt.Vertical, *args, **kwargs)


class LayoutBoxH(QtLayout):
    """Context manager for QHBoxLayout."""
    def __init__(self, *args, **kwargs):
        QtLayout.__init__(self, QtWidgets.QHBoxLayout, *args, **kwargs)


class LayoutBoxV(QtLayout):
    """Context manager for QVBoxLayout."""
    def __init__(self, *args, **kwargs):
        QtLayout.__init__(self, QtWidgets.QVBoxLayout, *args, **kwargs)


class WidgetLabel(QtWidget):
    """Context manager for QLabel."""
    def __init__(self, *args, **kwargs):
        QtWidget.__init__(self, QtWidgets.QLabel, *args, **kwargs)


def QLabel(*args, **kwargs):
    """Wrapper for QLabel."""
    with WidgetLabel(*args, **kwargs) as widget:
        return widget


class WidgetPushButton(QtWidget):
    """Context manager for QPushButton."""
    def __init__(self, *args, **kwargs):
        QtWidget.__init__(self, QtWidgets.QPushButton, *args, **kwargs)


def QPushButton(*args, **kwargs):
    """Wrapper for QPushButton."""
    with WidgetPushButton(*args, **kwargs) as widget:
        return widget


class WidgetLineEdit(QtWidget):
    """Context manager for QLineEdit."""
    def __init__(self, *args, **kwargs):
        QtWidget.__init__(self, QtWidgets.QLineEdit, *args, **kwargs)


def QLineEdit(*args, **kwargs):
    """Wrapper for QLineEdit."""
    with WidgetLineEdit(*args, **kwargs) as widget:
        return widget


class WidgetCheckBox(QtWidget):
    """Context manager for QtWidgets.QCheckBox."""
    def __init__(self, *args, **kwargs):
        QtWidget.__init__(self, QtWidgets.QCheckBox, *args, **kwargs)
    
    def __enter__(self):
        return QtWidget.__enter__(self, ['checkState', 'setChecked', 'isChecked'])


def QCheckBox(*args, **kwargs):
    """Wrapper for QtWidgets.QCheckBox."""
    with WidgetCheckBox(*args, **kwargs) as widget:
        return widget


class WidgetComboBox(QtWidget):
    """Context manager for QComboBox."""
    def __init__(self, *args, **kwargs):
        QtWidget.__init__(self, QtWidgets.QComboBox, *args, **kwargs)

    def __enter__(self):
        return QtWidget.__enter__(self, ['addItem', 'addItems'])


def QComboBox(*args, **kwargs):
    """Wrapper for QComboBox."""
    with WidgetComboBox(*args, **kwargs) as widget:
        return widget


class WidgetListWidget(QtWidget):
    """Context manager for QListWidget."""
    def __init__(self, *args, **kwargs):
        QtWidget.__init__(self, QtWidgets.QListWidget, *args, **kwargs)

    def __enter__(self):
        return QtWidget.__enter__(self, ['addItem', 'addItems'])


def QListWidget(*args, **kwargs):
    """Wrapper for QListWidget."""
    with WidgetListWidget(*args, **kwargs) as widget:
        return widget


def QStretch():
    """Wrapper for addStretch."""
    parent = Parent.get()
    parent.addStretch()


class WidgetTabGroup(QtWidget):
    """Context manager for QTabWidget."""
    def __init__(self, *args, **kwargs):
        QtWidget.__init__(self, QtWidgets.QTabWidget, *args, **kwargs)
        self._num_tabs = 0

    def __enter__(self):
        return QtWidget.__enter__(self, ['addTab'])


class WidgetTab(QtWidget):
    """Context manager for a tab (QWidget)."""
    def __init__(self, name='', *args, **kwargs):
        QtWidget.__init__(self, QtWidgets.QWidget, *args, **kwargs)
        if not isinstance(self.parent(), WidgetTabGroup):
            raise TypeError('incorrect parent type, expected "WidgetTabGroup", got "{}"'.format(self.parent().__class__.__name__))
        self._name = name

    def __enter__(self):
        QtWidget.__enter__(self, ['setLayout'])
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        parent = QtBase.__exit__(self, exc_type, exc_val, exc_tb)
        parent.addTab(self.QObject, self._name)


@contextmanager
def TabScrollLayout(*args, **kwargs):
    """Context manager for a new tab containing a scroll area."""
    with WidgetTab(*args, **kwargs) as tab_widget:
        tab_widget.setContentsMargins(0)
        with LayoutBoxV() as tab_layout:
            with WidgetScrollArea() as scroll_widget:
                with LayoutBoxV() as scroll_layout:
                    yield (tab_layout, scroll_widget, scroll_layout)


class WidgetScrollArea(QtWidget):
    """Context manager for QScrollArea."""
    def __init__(self, *args, **kwargs):
        QtWidget.__init__(self, QtWidgets.QScrollArea, *args, **kwargs)

    def __enter__(self):
        QtWidget.__enter__(self, ['setWidget', 'setWidgetResizable'])
        self.setWidgetResizable(True)
        return self


class WidgetGroupBox(QtWidget):
    """Context manager for QGroupBox."""
    def __init__(self, name=''):
        QtWidget.__init__(self, QtWidgets.QGroupBox, name)
        if not isinstance(self.parent(), QtBase):
            raise TypeError('incorrect parent type, expected "QtBase", got "{}"'.format(self.parent().__class__.__name__))