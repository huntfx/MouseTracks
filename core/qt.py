"""Helper functions for PySide/PyQt.
Very much WIP as I expand the functionality.

Naming Conventions:
    Layout Classes:                                                 #Context manager layout classes
        QtLayout                                                    #Base layout class, contains class overrides, yields layout
        Qt<widget>Layout                                            #Inherits QtLayout, contains __exit__ override, yields layout

    Layout Widgets:                                                 #Context manager layout widgets (both parent and children must be a layout)
        Q<widget>                                                   #Inherits QtLayout, contains __exit__ override, yields widget

    Combined Classes:                                               #Combined context manager widget and layout
        Qt<widget>Combined                                          #Inherits _QtLayoutCombinedBase, yields (widget, layout)
"""
from contextlib import contextmanager
from operator import methodcaller

from ext.Qt import QtWidgets, QtCore, QtGui
from core.compatibility import iteritems


def _get_and_del_kwargs(kwargs, values):
    """Return kwargs if exist and delete all allowed combinations."""
    result = None
    for value in values:
        if value in kwargs:
            result = kwargs.pop(value)
    return result


def convert_to_widget(layout):
    """Return a widget or convert a layout to a widget."""
    if isinstance(layout, QtLayout):
        layout = layout.layout
    if isinstance(layout, QtWidgets.QLayout):
        new = QtWidgets.QWidget()
        new.setLayout(layout)
        return new
    return layout


class WidgetFunctions(object):

    #Custom keywords that can be passed into widgets (must be a widget function)
    #The priority is used when some commands need to be executed before or after others
    KEYWORDS = {
        'min_width': (0, ['setMinimumWidth']),
        'max_width': (0, ['setMaximumWidth']),
        'min_height': (0, ['setMinimumHeight']),
        'max_height': (0, ['setMaximumHeight']),
        'fixed_width': (0, ['setFixedWidth']),
        'fixed_height': (0, ['setFixedHeight']),
        'fixed_size': (0, ['setFixedWidth', 'setFixedHeight']),
        'row': (0, ['setCurrentRow']),
        'enable': (0, ['setEnabled']),
        'visible': (0, ['setVisible']),
        'align': (0, ['setAlignment']),
        'resizable': (0, ['setResizable', 'setWidgetResizable']),
        'collapse': (0, ['setCollapsed']),
        'add_items': (-100, ['addItems']),
        'text': (0, ['setPlainText']),
        'css': (0, ['setStyleSheet']),
        'debug': (0, [])
    }
    KEYWORDS_SORT = [(k, v[1]) for k, v in sorted(iteritems(KEYWORDS), key=lambda kw: kw[1][0])]

    def __init__(self, widget, *args, **kwargs):
        """Create a widget with the provided arguments if possible."""
        if callable(widget):
            kwargs = {k: v for k, v in iteritems(kwargs) if k not in WidgetFunctions.KEYWORDS}
            self.widget = widget(*args, **kwargs)
        else:
            self.widget = widget

    def __call__(self, **kwargs):
        """Apply the custom keywords."""
        for keyword, funcs in self.KEYWORDS_SORT:
            if keyword in kwargs:
                for func in funcs:
                    try:
                        methodcaller(func, kwargs[keyword])(self.widget)
                    except AttributeError:
                        pass
        return self.widget


class QtLayout(object):
    """Easy way of building a layout with indentation.
    Subject to change as I learn more Qt so don't use this yet.

    Supported functions:
        QtLayout.add_label() <QLabel>
        QtLayout.add_button() <QPushButton>
        QtLayout.add_checkbox() <QCheckBox>
        QtLayout.add_textfield() <QLineEdit>
        QtLayout.add_radiobutton() <QRadioButton>
        QtLayout.add_list(list_values) <QListWidget>
        QtLayout.add_dropdown(dropdown_values) <QComboBox>
        QtLayout.add_stretch() <addStretch>
        QtTabGroupLayout(parent) <QTabWidget>
            QTab(parent, name) <QWidget>
                QtTabCombined(layout_function, parent, name) <QTab + QtLayout>
        QCollapsibleLayout <QCollapsibleMenu>
            QtCollapsibleLayoutCombined(layout_function, parent, name) <QCollapsibleLayout + QtLayout>       

    Supported Arguments:
        min_width <widget.setMinimumWidth>
        max_width <widget.setMaximumWidth>
        min_height <widget.setMinimumHeight>
        max_height <widget.setMaximumHeight>
        fixed_width <widget.setMinimumWidth + widget.setMaximumWidth>
        fixed_height <widget.setMinimumHeight + widget.setMaximumHeight>
        fixed_size <widget.setMinimumWidth + widget.setMaximumWidth + widget.setMinimumHeight + widget.setMaximumHeight>
        row <widget.setCurrentRow>
        visible <widget.setvisible>
        enable <widget.setEnabled>
        align <widget.setAlignment> (eg: QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

    Example Usage:
        Old way:
            self.push_button = QtWidgets.QPushButton("QPushButton")
            self.check_box_01 = QtWidgets.QCheckBox("QCheckBox 01")
            self.check_box_02 = QtWidgets.QCheckBox("QCheckBox 02")
            self.line_edit = QtWidgets.QLineEdit("QLineEdit")
            self.list_wdg = QtWidgets.QListWidget()
            self.list_wdg.addItems(["QListWidgetItem 01", "QListWidgetItem 02",  "QListWidgetItem 03", "QListWidgetItem 04"])
            self.list_wdg.setCurrentRow(0)
            self.list_wdg.setMaximumHeight(60)
            check_box_layout = QtWidgets.QHBoxLayout()
            check_box_layout.setContentsMargins(2, 2, 2, 2)
            check_box_layout.addWidget(self.check_box_01)
            check_box_layout.addWidget(self.check_box_02)
            main_layout = QtWidgets.QVBoxLayout()
            main_layout.setContentsMargins(6, 6, 6, 6)
            main_layout.addWidget(self.push_button)
            main_layout.addLayout(check_box_layout)
            main_layout.addWidget(self.line_edit)
            main_layout.addWidget(self.list_wdg)
            main_layout.addStretch()

        New way:
            with QtLayout(QtWidgets.QVBoxLayout, self) as main_layout:
                main_layout.margins = 6
                self.push_button = main_layout.add_button('QPushButton')
                with QtLayout(QtWidgets.QHBoxLayout, main_layout) as checkbox_layout:
                    checkbox_layout.margins = 2
                    self.check_box_01 = checkbox_layout.add_checkbox('QCheckBox 01')
                    self.check_box_02 = checkbox_layout.add_checkbox('QCheckBox 02')
                main_layout.add_stretch()
    """

    def __init__(self, func, parent=None, *args, **kwargs):
        self.parent = parent
        self._children = []
        self._css = {}

        self._layout = func
        self._args = args
        self._kwargs = kwargs
        
    def __enter__(self):
        #Check for diallowed widgets
        if self.__class__ == QtLayout:
            if self._layout == QtWidgets.QTabWidget:
                raise TypeError('"QtLayout(QWidgets.QTabWidget)" must be called as "QtTabGroupLayout()"')
        
        self.layout = WidgetFunctions(self._layout, *self._args, **self._kwargs)(**self._kwargs)
        return self
    
    def __exit__(self, *args):
        """Add current layout to the parent (if set).
        Handles different cases.
        """
        #if self._kwargs.get('debug', False) or True:
        #    print self.parent.layout, self.layout
        
        if self.parent is None:
            return
        try:
            self.parent._children.append(self.layout)
        except AttributeError:
            pass
            
        #Custom functions
        if isinstance(self.parent, (QBoxGroup, QTab, QCollapsibleLayout)):
            return self.parent.layout.setLayout(self.layout)
    
        if isinstance(self.parent, (QScrollZone, QtWidgets.QScrollArea)):
            return self.parent.layout.setWidget(convert_to_widget(self.layout))

        #Main function
        if isinstance(self.parent, QtLayout):
            if isinstance(self.parent.layout, QtWidgets.QSplitter):
                return self.parent.layout.addWidget(convert_to_widget(self.layout))

            if isinstance(self.parent.layout, QScrollZone):
                return self.parent.layout.setWidget(convert_to_widget(self.layout))

            if isinstance(self.layout, QtWidgets.QLayout):
                return self.parent.layout.addLayout(self.layout)

            if isinstance(self.layout, QtWidgets.QWidget):
                return self.parent.layout.addWidget(self.layout)

            return self.parent.layout.setLayout(self.layout)
        
        #Main window
        if isinstance(self.layout, QtWidgets.QWidget):
            return self.parent.setCentralWidget(self.layout)
        if isinstance(self.parent, QtWidgets.QLayout):
            return self.parent.addLayout(self.layout)
        return self.parent.setLayout(self.layout)

    @property
    def margins(self):
        return self.layout.getContentsMargins()

    @margins.setter
    def margins(self, margins):
        if isinstance(margins, QtCore.QMargins):
            return self.layout.setContentsMargins(margins)
        if isinstance(margins, (list, tuple)):
            return self.layout.setContentsMargins(*margins)
        return self.layout.setContentsMargins(margins, margins, margins, margins)

    @property
    def spacing(self):
        return self.layout.spacing()

    @spacing.setter
    def spacing(self, spacing):
        self.layout.setSpacing(spacing)
    
    def set_size_policy(self, horizontal, vertical=None):
        """Set the size policy.

        Main ones:
            QtWidgets.QSizePolicy.Minimum: Will not shrink below default.
            QtWidgets.QSizePolicy.Maximum: Will not expand above default.
    
        Documentation: http://pyqt.sourceforge.net/Docs/PyQt4/qsizepolicy.html

        """
        if vertical is None:
            vertical = horizontal
        return self.layout.setSizePolicy(QtWidgets.QSizePolicy(horizontal, vertical))

    def add_widget(self, widget, *args, **kwargs):
        """Add any widget with the custom keywords."""
        custom_parent = kwargs.pop('parent', None)
        wgt = WidgetFunctions(widget, *args, **kwargs)(**kwargs)
        if isinstance(self.layout, QtWidgets.QScrollArea):
            if len(self._children) > 1:
                raise RuntimeError('too many child widgets')
            self.layout.setWidget(wgt)
        else:
            self.layout.addWidget(wgt)
        self._children.append(wgt)

        return wgt
    
    def add_layout(self, layout, *args, **kwargs):
        """Add a layout as a widget if resizing or anything else is important.
        To do this, initialise the QtLayout as normal, but do not provide a parent.
        Instead send the instance to parent.add_layout.
        """
        return self.add_widget(convert_to_widget(layout), *args, **kwargs)

    def add_label(self, *args, **kwargs):
        return self.add_widget(QtWidgets.QLabel, *args, **kwargs)

    def add_button(self, *args, **kwargs):
        return self.add_widget(QtWidgets.QPushButton, *args, **kwargs)
    
    def add_checkbox(self, *args, **kwargs):
        return self.add_widget(QtWidgets.QCheckBox, *args, **kwargs)
    
    def add_textfield(self, *args, **kwargs):
        return self.add_widget(QtWidgets.QLineEdit, *args, **kwargs)
    
    def add_textarea(self, *args, **kwargs):
        return self.add_widget(QtWidgets.QTextEdit, *args, **kwargs)

    def add_radiobutton(self, *args, **kwargs):
        return self.add_widget(QtWidgets.QRadioButton, *args, **kwargs)

    def add_slider(self, *args, **kwargs):
        orientation = None
        horizontal = _get_and_del_kwargs(kwargs, ['h', 'horizontal'])
        vertical = _get_and_del_kwargs(kwargs, ['v', 'vertical'])
        if vertical or not horizontal and horizontal is not None:
            orientation = QtCore.Qt.Orientation.Vertical
        else:
            orientation = QtCore.Qt.Orientation.Horizontal
        return self.add_widget(QtWidgets.QSlider, orientation, *args, **kwargs)
    
    def add_list(self, items=[], *args, **kwargs):
        kwargs.update({'add_items': items})
        return self.add_widget(QtWidgets.QListWidget, *args, **kwargs)
    
    def add_dropdown(self, items=[], *args, **kwargs):
        kwargs.update({'add_items': items})
        return self.add_widget(QtWidgets.QComboBox, *args, **kwargs)

    def add_stretch(self, *args, **kwargs):
        return self.layout.addStretch()

    def add_menu_item(self, name, parent=None, checkable=False):
        """Add an item to a menu, creating the main bar if required."""
        if parent is None:
            try:
                parent = self._menu_bar
            except AttributeError:
                parent = self._menu_bar = QtWidgets.QMenuBar()
                self.layout.insertWidget(0, self._menu_bar)

        #Checkbox menu item
        if checkable and not isinstance(parent, QtWidgets.QMenuBar):
            return parent.addAction(QtWidgets.QAction(name, parent, checkable=True))

        return parent.addMenu(name)

    def set_css(self, stylesheet=None):
        """Set a custom stylesheet or use the saved data.
        Using a custom one will overwrite the saved data.
        """
        if stylesheet is None:
            stylesheet = self.layout.__class__.__name__ + '{' + ' '.join('{}: {};'.format(k, v) for k, v in iteritems(self._css)) + '}'
        else:
            self._css = {}
        self.layout.setStyleSheet(stylesheet)    

    def add_css(self, **kwargs):
        kwargs = {k.replace('_', '-'): v for k, v in iteritems(kwargs)}
        self._css.update(kwargs)
        self.set_css()

    def remove_border(self):
        """Remove the border of the layout/widget.
        So far only tested on QTabWidget.
        """
        self._css['border'] = 0
        self.set_css()

    def set_font_bold(self):
        self._css['font-weight'] = 'bold'
        self.set_css()
    
    def set_font_normal(self):
        self._css['font-weight'] = 'normal'
        self.set_css()
    
    def set_stretch_factor(self, value):
        """Set the stretch factor of the most recently added layout (for QtWidgets.QSplitter)."""
        index = len(self._children) - 1
        self.layout.setStretchFactor(index, value)
    
    def set_index(self, index):
        """Set the current index (for QtWidgets.QTabWidget)."""
        self.layout.setCurrentIndex(index)


class QtTabGroupLayout(QtLayout):
    """Create a tab group context manager.
    Use QTab for each tab.
    """
    def __init__(self, parent, *args, **kwargs):
        if not isinstance(parent, QtLayout) or isinstance(parent, self.__class__):
            raise TypeError('incorrect parent type, expected "QtLayout", got "{}"'.format(parent.__class__.__name__))
        super(self.__class__, self).__init__(QtWidgets.QTabWidget, parent=parent, *args, **kwargs)


class QTab(QtLayout):
    """Create a tab context manager.
    Recommended to use QtTabCombined instead.
    
    Example Usage:
        with QtTabGroupLayout(parent_layout) as tab_group:
            with Qtab(tab_group, 'Tab 1') as current_tab:
                with QtLayout(QtWidgets.QBoxLayout, current_tab) as tab_layout:

    Alternative Usage:
        with QtTabGroupLayout(parent_layout) as tab_group:
            with QtTabCombined(QtWidgets.QVBoxLayout, tab_group) as (tab_widget, tab_layout):
    """
    def __init__(self, parent, name, *args, **kwargs):
        if not (isinstance(parent, QtLayout) and isinstance(parent.layout, QtWidgets.QTabWidget)):
            raise TypeError('incorrect parent type, expected "QtLayout(QtWidgets.QTabWidget)", got "{}"'.format(parent.__class__.__name__))

        self.name = name
        super(self.__class__, self).__init__(QtWidgets.QWidget, parent=parent, *args, **kwargs)

    def __exit__(self, *args):
        return self.parent.layout.addTab(self.layout, self.name)


class QScrollZone(QtLayout):
    """Create a scroll area context manager.
    Recommended to use QtScrollZoneCombined instead.
    
    Example Usage:
        with QScrollArea(parent, fixed_height=100) as scroll_area:
            with QtLayout(QtWidgets.QVBoxLayout, scroll_area) as box_layout:
    
    Alternative Usage:
        pqt.QtScrollZoneCombined(QtWidgets.QVBoxLayout, parent, fixed_height=100) as (scroll_area, box_layout):

    Old Way:
        #Convert layout to widget
        frame = QtWidgets.QFrame()
        frame.setLayout(check_box_layout)
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(frame)
        scroll.setFixedHeight(30)
        layout.addWidget(scroll)
    """
    def __init__(self, parent, resizable=True, *args, **kwargs):
        if not isinstance(parent, QtLayout):
            raise TypeError('incorrect parent type, expected "QtLayout", got "{}"'.format(parent.__class__.__name__))
        kwargs.update({'resizable': resizable})
        super(self.__class__, self).__init__(QtWidgets.QScrollArea, parent=parent, *args, **kwargs)

    def __exit__(self, *args):
        print(self.parent, self.parent.layout)
        self.parent.layout.addWidget(self.layout)

class QCollapsibleLayout(QtLayout):
    """Create a QCollapsibleMenu context manager.
    
    Usage Example:
        with QCollapsibleLayout(parent) as frame_layout:
            with QtLayout(QtWidgets.QVBoxLayout, frame_layout) as content_layout:
                content_layout.add()
    
    Alternative Usage:
    """
    def __init__(self, parent, name='', collapse=False, *args, **kwargs):
        #For some reason if you pass in parent and name as args it crashes, so do this instead
        kwargs.update({'parent': parent, 'name': name, 'collapse': collapse})
        super(self.__class__, self).__init__(QCollapsibleMenu, *args, **kwargs)
        self.name = name

    def __exit__(self, *args):
        self.layout.title = self.name
        return self.parent.layout.addWidget(self.layout)

        
class QBoxGroup(QtLayout):
    def __init__(self, parent, *args, **kwargs):
        if not isinstance(parent, QtLayout):
            raise TypeError('incorrect parent type, expected "QtLayout", got "{}"'.format(parent.__class__.__name__))
        super(self.__class__, self).__init__(QtWidgets.QGroupBox, parent, *args, **kwargs)
    
    def __exit__(self, *args):
        return self.parent.layout.addWidget(self.layout)
        

class QtResizableLayout(QtLayout):
    def __init__(self, parent, orientation, *args, **kwargs):
        super(QtResizableLayout, self).__init__(QtWidgets.QSplitter, parent, orientation, *args, **kwargs)


class QtHResizableLayout(QtResizableLayout):
    def __init__(self, parent, *args, **kwargs):
        super(QtHResizableLayout, self).__init__(parent, QtCore.Qt.Horizontal, *args, **kwargs)


class QtVResizableLayout(QtResizableLayout):
    def __init__(self, parent, *args, **kwargs):
        super(QtVResizableLayout, self).__init__(parent, QtCore.Qt.Vertical, *args, **kwargs)


@contextmanager
def _QtLayoutCombinedBase(func_1_data, func_2_data):
    """Group more than one context manager together.
    Requires the second context manager to be a QtLayout object, 
    where func_2 in is the widget to use.

    Will return both parent controls as a tuple.

    Parameters:
        func_1: Parent context manager.
        func_2: Widget to pass into QtLayout.
                The result from func_1 will also be passed in.
        args_x: Arguments for each function.
        kwargs_x: Keyword arguments for each function.

    Example Usage:
        Original way:
            with func_1(n) as x:
                with func_2(x) as y:
        This way:
            with func(n) as (x, y):

    Source: https://stackoverflow.com/a/45681273/2403000
    """
    func_1, args_1, kwargs_1 = func_1_data
    func_2, args_2, kwargs_2 = func_2_data
    with func_1(*args_1, **kwargs_1) as layout_1, QtLayout(func_2, layout_1, *args_2, **kwargs_2) as layout_2:
        yield (layout_1, layout_2)


@contextmanager
def QtCollapsibleLayoutCombined(layout_func, parent, name='', collapse=False, *args, **kwargs):
    """Group a collapible menu with a layout.
    
    Example:
        with QtCollapsibleLayoutCombined(QtWidgets.QVBoxLayout, parent_layout) as (widget, layout):
            #do stuff
    """
    kwargs.update({'parent': parent, 'name': name, 'collapse': collapse})
    func_1 = [QCollapsibleLayout, args, kwargs]
    func_2 = [layout_func, (), {}]
    with _QtLayoutCombinedBase(func_1, func_2) as (frame_widget, frame_layout):
        yield (frame_widget, frame_layout)


@contextmanager
def QtTabCombined(layout_func, parent, name='', *args, **kwargs):
    """Group a tab with a layout.
    Must be inside a QtWidgets.QTabWidget object.
    
    Example:
        with QtLayout(QtWidgets.QTabWidget, parent_layout) as tab_group:
            with QtTabCombined(QtWidgets.QVBoxLayout, tab_group) as (widget, layout):
                #do stuff
    """
    kwargs.update({'parent': parent, 'name': name})
    func_1 = [QTab, args, kwargs]
    func_2 = [layout_func, (), {}]
    with _QtLayoutCombinedBase(func_1, func_2) as (tab_widget, tab_layout):
        yield (tab_widget, tab_layout)


@contextmanager
def QtTabGroupCombined(layout_func, parent, margin=0, *args, **kwargs):
    """Group a tab group with a layout."""
    if isinstance(parent, QtLayout):
        raise TypeError('incorrect parent type, not to be used with "QtLayout" instances')

    kwargs.update({'parent': parent})
    with QtLayout(layout_func, parent) as layout, QtLayout(QtWidgets.QTabWidget, layout) as tab_group:
        layout.margins = layout.spacing = margin
        yield tab_group


@contextmanager
def QtScrollZoneCombined(layout_func, parent, *args, **kwargs):
    """Group a collapible menu with a layout.
    Must be inside a QtLayout object.

    Example:
        with QtScrollZoneCombined(QtWidgets.QVBoxLayout, parent_layout) as (scroll_widget, box_layout):
            #do stuff
    """
    kwargs.update({'parent': parent})
    func_1 = [QScrollZone, args, kwargs]
    func_2 = [layout_func, (), {}]
    with _QtLayoutCombinedBase(func_1, func_2) as (scroll_widget, scroll_layout):
        yield (scroll_widget, scroll_layout)


@contextmanager
def QtMayaAttributeLayout(parent, margins=None):
    """Base layout for working in the attribute editor."""
    with QtLayout(QtWidgets.QVBoxLayout, parent) as parent_layout, QtScrollZoneCombined(QtWidgets.QVBoxLayout, parent_layout) as (scroll_area, main_layout):
        parent_layout.margins = 0
        scroll_area.set_size_policy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        if margins:
            scroll_area.margins = scroll_area.spacing = margins
        main_layout.spacing = 2
        yield main_layout
                

class QCollapsibleMenu(QtWidgets.QWidget):
    """Create a collapsible menu to mimic Maya's FrameLayout widget.

    Source: https://kiwamiden.com/make-mayas-framelayout-with-pyside
    """
    _BASE_HEIGHT = 20
    def __init__(self, parent=None, name='', *args, **kwargs):
        super(self.__class__, self).__init__(parent, *args, **kwargs)

        self.name = name
         
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, self._BASE_HEIGHT, 0, 0)
        layout.setSpacing(0)
        super(self.__class__, self).setLayout(layout)

        self.__widget = QtWidgets.QFrame(parent)
        self.__widget.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.__widget.setFrameShadow(QtWidgets.QFrame.Plain)
        self.__widget.setLineWidth(0)
        layout.addWidget(self.__widget)
         
        self.__collapsed = False

    def setLayout(self, layout):
        self.__widget.setLayout(layout)
         
    def expandCollapseRect(self):
        return QtCore.QRect(0, 0, self.width(), self._BASE_HEIGHT)
 
    def mouseReleaseEvent(self, event):
        if self.expandCollapseRect().contains(event.pos()):
            self.toggleCollapsed()
            event.accept()
        else:
            event.ignore()
     
    def toggleCollapsed(self):
        self.setCollapsed(not self.__collapsed)
         
    def setCollapsed(self, state=True):
        self.__collapsed = state
 
        if state:
            self.setMinimumHeight(self._BASE_HEIGHT)
            self.setMaximumHeight(self._BASE_HEIGHT)
            self.__widget.setVisible(False)
        else:
            self.setMinimumHeight(0)
            self.setMaximumHeight(1000000)
            self.__widget.setVisible(True)

    def paintEvent(self, event):
        painter = QtGui.QPainter()
        painter.begin(self)
         
        font = painter.font()
        font.setBold(True)
        painter.setFont(font)
 
        x = self.rect().x()
        y = self.rect().y()
        w = self.rect().width()
        offset = 25
         
        painter.setRenderHint(painter.Antialiasing)
        painter.fillRect(self.expandCollapseRect(), QtGui.QColor(*[93] * 3))
        painter.drawText(x+offset, y+3, w, 16,
                         QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop,
                         self.name)
        self.__drawTriangle(painter, x, y)
        painter.setRenderHint(QtGui.QPainter.Antialiasing, False)
        painter.end()
         
    def __drawTriangle(self, painter, x, y):       
        if not self.__collapsed:
            points = [QtCore.QPoint(x+5, y+7),
                      QtCore.QPoint(x+17, y+7),
                      QtCore.QPoint(x+11, y+13)]
             
        else:
            points = [QtCore.QPoint(x+8, y+4),
                      QtCore.QPoint(x+14, y+10),
                      QtCore.QPoint(x+8, y+16)]
             
        currentBrush = painter.brush()
        currentPen = painter.pen()
         
        painter.setBrush(QtGui.QBrush(QtGui.QColor(*[230] * 3), QtCore.Qt.SolidPattern))
        painter.setPen(QtGui.QPen(QtCore.Qt.NoPen))
        painter.drawPolygon(QtGui.QPolygon(points))
        painter.setBrush(currentBrush)
        painter.setPen(currentPen)
