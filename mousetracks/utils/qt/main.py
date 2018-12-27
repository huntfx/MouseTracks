from __future__ import absolute_import

from contextlib import contextmanager

from .Qt import QtWidgets, QtCore
from ..compatibility import iteritems


def layoutToWidget(layout):
    """Return a widget or convert a layout to a widget."""
    if isinstance(layout, QtBase):
        layout = layout.QObject
    if isinstance(layout, QtWidgets.QLayout):
        new = QtWidgets.QWidget()
        new.setLayout(layout)
        return new
    return layout


class Mixins(object):
    """Define any commonly used functions that may need to be added to widgets."""
    class AddLayout(object):
        def addLayout(self, layout):
            self.addWidget(layoutToWidget(layout))


class QtBase(object):
    COPY_METHODS = {
        QtWidgets.QLayout: [
            'setSpacing',
            'addStretch'
        ],
        QtWidgets.QWidget: [
            'setVisible',
            'setEnabled'
        ],
        QtWidgets.QComboBox: [
            'addItems'
        ],
        QtWidgets.QScrollArea: [
            'setWidgetResizable'
        ],
        QtWidgets.QCheckBox: [
            'setChecked'
        ]
    }

    def __init__(self, func, parent=None, *args, **kwargs):
        if isinstance(func, QtBase):
            print('QtCustom.{}()'.format(func.__class__.__name__))
            self.QObject = func.QObject
        else:
            print('{}()'.format(func.__class__.__name__))
            self.QObject = func
        
        for widget_class, funcs in iteritems(self.COPY_METHODS):
            if widget_class is None or isinstance(self.QObject, widget_class):
                for func in funcs:
                    setattr(self, func, getattr(self.QObject, func))

    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        pass

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
            margins = [i if i is not None else j for i, j in zip(margins, self.QObject.getContentsMargins())]
        self.QObject.setContentsMargins(*margins)



class QtLayout(QtBase):
    def __init__(self, func, parent=None, *args, **kwargs):
        super(QtLayout, self).__init__(func, parent, *args, **kwargs)

        if parent is not None:
            if isinstance(parent, QtWidgets.QMainWindow):
                print('{}.setCentralWidget(layoutToWidget({}))'.format(parent.__class__.__name__, self.QObject.__class__.__name__))
                parent.setCentralWidget(layoutToWidget(self.QObject))
            elif isinstance(parent, (QtTabLayout, QtTabWidget, QtGroupBoxWidget)):
                print('{}.setLayout({})'.format(parent.QObject.__class__.__name__, self.QObject.__class__.__name__))
                parent.QObject.setLayout(self.QObject)
            elif isinstance(parent, QtScrollWidget):
                print('{}.setWidget(layoutToWidget({}))'.format(parent.QObject.__class__.__name__, self.QObject.__class__.__name__))
                parent.QObject.setWidget(layoutToWidget(self.QObject))
            elif isinstance(parent, QtLayout):
                print('{}.addLayout({})'.format(parent.QObject.__class__.__name__, self.QObject.__class__.__name__))
                parent.QObject.addLayout(self.QObject)
            else:
                print('Unknown parent (layout): {}'.format(parent))

    def _addLayout(self, layout, *args, **kwargs):
        with QtLayout(layout, parent=self, *args, **kwargs) as layout:
            return layout

    def _addWidget(self, widget, *args, **kwargs):
        with QtWidget(widget, self, *args, **kwargs) as widget:
            return widget

    @contextmanager
    def addLayout(self, layout, *args, **kwargs):
        """Add a layout."""
        yield self._addLayout(layout, *args, **kwargs)

    def addLayoutWidget(self, layout, *args, **kwargs):
        """Add a layout that does not contain anything."""
        return self._addLayout(layout, *args, **kwargs)

    def addWidget(self, widget, *args, **kwargs):
        """Add a widget."""
        return self._addWidget(widget, *args, **kwargs)

    @contextmanager
    def addWidgetLayout(self, widget, *args, **kwargs):
        """Add a widget that is used like a layout."""
        yield self._addWidget(widget, *args, **kwargs)

    @contextmanager
    def addTabGroup(self):
        with QtTabLayout(self) as widget:
            yield widget

    @contextmanager
    def addScrollArea(self, layout):
        with QtScrollWidget(self) as container_widget, QtLayout(layout, container_widget) as container_layout:
            yield (container_widget, container_layout)

    @contextmanager
    def addGroupBox(self, layout, name=''):
        with QtGroupBoxWidget(self, name) as container_widget, QtLayout(layout, container_widget) as container_layout:
            yield (container_widget, container_layout)
        

class QtWidget(QtBase):
    def __init__(self, func, parent=None, *args, **kwargs):
        super(QtWidget, self).__init__(func, None, *args, **kwargs)

        if parent is not None:
            if isinstance(parent, QtWidgets.QMainWindow):
                print('{}.setCentralWidget({})'.format(parent.QObject.__class__.__name__, self.QObject.__class__.__name__))
                parent.setCentralWidget(self.QObject)
            elif isinstance(parent, QtTabLayout):
                pass
            elif isinstance(parent, QtLayout):
                print('{}.addWidget({})'.format(parent.QObject.__class__.__name__, self.QObject.__class__.__name__))
                parent.QObject.addWidget(self.QObject)
            else:
                print('Unknown parent (widget): {}'.format(parent))



class QtGroupBoxWidget(QtWidget):
    """Modified QtWidget class for using a QGroupBox."""
    def __init__(self, parent=None, name=''):
        QtWidget.__init__(self, QtWidgets.QGroupBox(name), parent)


class QtScrollWidget(QtWidget):
    """Modified QtWidget class for using a QScrollArea."""
    def __init__(self, parent=None, *args, **kwargs):
        QtWidget.__init__(self, QtWidgets.QScrollArea(), parent, *args, **kwargs)
        self.setWidgetResizable(True)


class QtTabWidget(QtWidget):
    """Modified QtWidget class for using tabs."""
    def __init__(self, parent=None, *args, **kwargs):
        QtWidget.__init__(self, QtWidgets.QWidget(), parent, *args, **kwargs)


class QtTabLayout(QtWidget):
    """Modified QtWidget class for using a tab group."""
    def __init__(self, parent=None, *args, **kwargs):
        QtWidget.__init__(self, QtWidgets.QTabWidget(), parent, *args, **kwargs)

    @contextmanager
    def addTab(self, layout, name=''):
        with QtTabWidget(self) as container_widget, QtLayout(layout, container_widget) as container_layout:
            self.QObject.addTab(container_widget.QObject, name)
            yield (container_widget, container_layout)

    def setFixedWidth(self, *args, **kwargs):
        self.QObject.setFixedWidth(*args, **kwargs)