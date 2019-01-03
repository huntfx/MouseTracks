"""Standalone widgets for use in Qt applications.


ResizableImage:
    Subclass of QLabel that is meant to be an image that fills the available space.
    Usage:
        ri = ResizableImage(path_to_image)
        with ri.makeEditable():
            ri.setPixel(x, y, QtGui.QColor(r, g, b).rgb())
        layout.addWidget(ri)


AutoGrid:
    Subclass of QScrollArea to contain a grid of widgets with a dynamic layout.
    Other widgets, such as a slider, can control the "zoom" by calling setGridSize.
    
    Usage:
        grid = AutoGrid()
        grid.setMaximumWidgetWidth(512)
        grid.setSpacing(0)

        for image_path in all_images:
            btn = QtWidgets.QPushButton()
            btn.setIcon(QtGui.QIcon(QtGui.QPixmap(image_path)))
            grid.addWidget(btn)

        layout.addWidget(grid)
"""

from __future__ import absolute_import

from contextlib import contextmanager
from functools import partial

from .Qt import QtWidgets, QtCore, QtGui


class ResizableImage(QtWidgets.QLabel):

    def __init__(self, pixmap=None, parent=None, minimumSize=(1, 1), align=QtCore.Qt.AlignCenter):
        super(ResizableImage, self).__init__(parent)
        self.setMinimumSize(*minimumSize)
        self.setAlignment(align)

        self._pixmapOriginal = None
        if pixmap is not None:
            self.setPixmap(pixmap)

    def resizeEvent(self, event):
        """Resize the pixmap if it exists, keeping the aspect ratio."""
        if self._pixmapOriginal is not None:
            #Test to make a square in the top left corner
            with self.makeEditable():
                colour = QtGui.QColor(255, 255, 255).rgb()
                for x in range(50):
                    for y in range(50):
                        self.setPixel(x, y, colour)

            size_mult = min(self.width() / self._pixmapWidth, self.height() / self._pixmapHeight)
            scaled_pixmap = self._pixmapOriginal.scaled(self._pixmapWidth * size_mult, self._pixmapHeight * size_mult, QtCore.Qt.IgnoreAspectRatio, QtCore.Qt.SmoothTransformation)
            super(ResizableImage, self).setPixmap(scaled_pixmap)

        return super(ResizableImage, self).resizeEvent(event)

    @contextmanager
    def makeEditable(self):
        """Convert the pixmap to an image to perform pixel editing operations.
        On finish, it will update the default pixmap.
        """
        if self._pixmapOriginal is not None:
            self._pixmapImage = self._pixmapOriginal.toImage()
        yield self
        if self._pixmapImage is not None:
            self.setPixmap(QtGui.QPixmap.fromImage(self._pixmapImage))

    def setPixel(self, *args, **kwargs):
        """Access the setPixel command of the pixmap."""
        if self._pixmapImage is not None:
            self._pixmapImage.setPixel(*args, **kwargs)

    def setPixmap(self, pixmap):
        """Set the pixmap and store information for resizing."""
        if isinstance(pixmap, str):
            pixmap = QtGui.QPixmap(pixmap)
        self._pixmapOriginal = pixmap
        self._pixmapWidth = pixmap.width()
        self._pixmapHeight = pixmap.height()
        self._pixmapImage = None

        #Cancel if the pixmap is empty
        if not self._pixmapWidth or not self._pixmapHeight:
            self._pixmapOriginal = None
            return

        super(ResizableImage, self).setPixmap(pixmap)



class AutoGrid(QtWidgets.QScrollArea):
    """Arrange widgets and move to new row if there is not enough room.

    Main Methods:
        addWidget(QtWidgets.QWidget)
        addLayout(QtWidgets.QLayout)
        removeItem(QtWidgets.QWidget|QtWidgets.QLayout)
        removeWidget(QtWidgets.QWidget|QtWidgets.QLayout)
        removeLayout(QtWidgets.QWidget|QtWidgets.QLayout)

    Supported Methods:
        setAspectRatio
        
    Additional Methods:
        setMinimumItemWidth(int): Set the minimum width allowed for items.
            Default: None
            Query: minimumItemWidth()
        setMaximumItemWidth(int): Set the maximum width allowed for items.
            Default: None
            Query: maximumItemWidth()
        setMinimumItemHeight(int): Set the minimum height allowed for items.
            Default: None
            Query: minimumItemHeight()
        setMaximumItemHeight(int): Set the maximum height allowed for items.
            Default: None
            Query: maximumItemHeight()
        setZoomSpeed(float): Set the zoom power of the scroll wheel.
            Default: 1
            Query: zoomSpeed()
        setContentsMargins(QtCore.QMargins|int): Set the contents margins of the grid.
            Default: 0
            Query: contentsMargins()
        setSpacing(int): Set spacing between each grid item.
            Default: 0
            Query: spacing()
        setTextPadding(int): Set padding between the text and widget.
            Default: 5
            Query: textPadding()
        setGridSize(int): Set the height of each widget.
            Default: 250
            Query: gridSize()
        index(int): Get the item at the current index
            Query: indexOf(QtWidgets.QWidget|QtWidgets.QLayout): Get the current item index
        row(int): Get the items in the current row.
            Query: rowOf(QtWidgets.QWidget|QtWidgets.QLayout): Get the current item row
            WARNING: Will not work if window has not finished loading.
        column(int): Get the items in the current column (column meaning 'x' spaces from the left)
            Query: columnOf(QtWidgets.QWidget|QtWidgets.QLayout): Get the current item column
            WARNING: Will not work if window has not finished loading.
    """

    TYPE_WIDGET = 0
    TYPE_LAYOUT = 1

    def __init__(self, parent=None):
        super(AutoGrid, self).__init__(parent)
        self._widgetReady = False
        self._itemList = {
            None: {
                'type': -1,
                'order': -1,
                'aspect': 0,
                'width': 0,
                'height': 0
            }
        }
        self._itemOrder = []
        self._scrollBarWidth = int(QtWidgets.QScrollBar().sizeHint().width())
        self._maxAspect = 0

        #Custom methods
        self.setMaximumItemWidth()
        self.setMaximumItemHeight()
        self.setMinimumItemWidth()
        self.setMinimumItemHeight()
        self.setContentsMargins(0)
        self.setTextPadding(5)
        self.setSpacing(5)
        self.setGridSize(250)
        self.setZoomSpeed(1)

        #Inbuilt Qt methods
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setAlignment(QtCore.Qt.AlignHCenter)

        self._widgetReady = True

    @staticmethod
    def _paintEventOverride(self, old_paint, text, event):
        """Override paintEvent on widgets to also draw text."""
        old_paint(event)
        text_flags = QtCore.Qt.AlignHCenter | QtCore.Qt.AlignBottom  | QtCore.Qt.TextWordWrap

        #Setup font
        font = QtGui.QFont()
        font.setBold(True)
        font.setCapitalization(QtGui.QFont.AllUppercase)
        font_size = self.height() ** 0.6
        font.setPixelSize(font_size)

        #Setup painter
        painter = QtGui.QPainter(self)
        painter.setFont(font)

        #Draw text
        shadow_offset = max(1, round(font_size / 10))
        padding = self.autoGridTextPadding()
        width = self.width() - padding * 2 - shadow_offset
        height = self.height() - padding * 2 - shadow_offset
        painter.setPen(QtGui.QColor(0, 0, 0))
        painter.drawText(QtCore.QRect(padding+shadow_offset, padding+shadow_offset, width, height), text_flags, text)
        painter.setPen(QtGui.QColor(255, 255, 255))
        painter.drawText(QtCore.QRect(padding, padding, width, height), text_flags, text)

        painter.setBackground(QtGui.QColor(0, 0, 0))

    def setGridSize(self, size):
        self._gridSize = size

        #Limit values
        if self._minimumItemAdjustedHeight is not None and self._minimumItemAdjustedHeight > self._gridSize:
            self._gridSize = self._minimumItemAdjustedHeight
        if self._minimumItemHeight is not None and self._minimumItemHeight > self._gridSize:
            self._gridSize = self._minimumItemHeight
        if self._maximumItemAdjustedHeight is not None and self._maximumItemAdjustedHeight < self._gridSize:
            self._gridSize = self._maximumItemAdjustedHeight
        if self._maximumItemHeight is not None and self._maximumItemHeight < self._gridSize:
            self._gridSize = self._maximumItemHeight

        self._minimumWidth = 0
        self._resizeImages()
        self.resizeEvent()

    def gridSize(self):
        return self._gridSize

    def setTextPadding(self, padding=0):
        self._textPadding = padding

    def textPadding(self):
        return self._textPadding

    def _addItem(self, item, text, aspectRatio, itemType):
        if item not in self._itemList:
            
            #Override the paint method
            if text and hasattr(item, 'paintEvent'):
                old_paint = item.paintEvent
                item.autoGridTextPadding = self.textPadding
                item.paintEvent = partial(self._paintEventOverride, item, old_paint, text)
            
            #Calculate button ratio
            icon_sizes = item.icon().availableSizes()
            if icon_sizes:
                size = max(icon_sizes)
                width = size.width()
                height = size.height()
            else:
                width = self.width()
                height = self.height()
            aspectRatio = aspectRatio or width / height
            self._maxAspect = max(self._maxAspect, aspectRatio)

            self._itemList[item] = {
                'type': itemType, 
                'aspect': aspectRatio,
                'original_icon': item.icon(),
                'original_icon_size': size if icon_sizes else None,
                'current_row': -1,
                'current_column': -1,
            }
            self._itemOrder.append(item)
            self._resizeImages(item)
            self.setMinimumItemWidth(self.minimumItemWidth())
            self.setMaximumItemWidth(self.maximumItemWidth())
    
    def _resizeImages(self, *items):
        """Resize an image for the current row height."""
        for item in (items or self._itemList):
            if item is not None:
                new_width = self._gridSize * self._itemList[item]['aspect']
                new_size = QtCore.QSize(new_width, self._gridSize)

                if self._itemList[item]['original_icon_size'] is not None:
                    too_short = self._itemList[item]['original_icon_size'].height() < self._gridSize
                    too_thin = self._itemList[item]['original_icon_size'].width() < self._gridSize * self._itemList[item]['aspect']
                    if too_short or too_thin:
                        pixmap = self._itemList[item]['original_icon'].pixmap(self._itemList[item]['original_icon_size']).scaledToHeight(self._gridSize)
                        item.setIcon(pixmap)

                item.setFixedSize(new_size)
                item.setIconSize(new_size)
                self._itemList[item]['width'] = new_width
                self._itemList[item]['height'] = self._gridSize
                self.setMinimumWidth(new_width)

    def addWidget(self, widget, text='', aspectRatio=None):
        self._addItem(widget, text=text, aspectRatio=aspectRatio, itemType=self.TYPE_WIDGET)

    def addLayout(self, layout, text='', aspectRatio=None):
        self._addItem(layout, text=text, aspectRatio=aspectRatio, itemType=self.TYPE_LAYOUT)

    def setMinimumWidth(self, width):
        width += self._scrollBarWidth + self._contentsWidth + 5
        if width > getattr(self, '_minimumWidth', 0):
            self._minimumWidth = width
            super(AutoGrid, self).setMinimumWidth(width)

    def setContentsMargins(self, left=None, top=None, right=None, bottom=None):
        if isinstance(left, QtCore.QMargins):
            self._contentsMargins = left
        elif left is not None and top is None and right is None and bottom is None:
            self._contentsMargins = QtCore.QMargins(left, left, left, left)
        elif left is not None and top is not None and right is not None and bottom is not None:
            self._contentsMargins = QtCore.QMargins(left, top, right, bottom)
        else:
            raise ValueError('invalid content margins')
        self._contentsWidth = self._contentsMargins.right() + self._contentsMargins.left()

    def contentsMargins(self):
        return self._contenstMargins

    def setSpacing(self, spacing):
        self._spacing = spacing

    def spacing(self):
        return self._spacing

    def contentsWidth(self):
        return self.width() - self._contentsWidth - self._scrollBarWidth

    def buildLayout(self):
        if not self._itemOrder:
            return

        #Get alignment information
        alignment = self.alignment()
        align_h = [bool(alignment & QtCore.Qt.AlignLeft), bool(alignment & QtCore.Qt.AlignHCenter), bool(alignment & QtCore.Qt.AlignRight)]
        align_v = [bool(alignment & QtCore.Qt.AlignTop), bool(alignment & QtCore.Qt.AlignVCenter), bool(alignment & QtCore.Qt.AlignBottom)]
        #Set defaults to match the normal widget behaviour
        if not any(align_h):
            align_h[0] = True
        if not any(align_v):
            align_v[0] = True

        #Setup main grid
        max_width = self.contentsWidth()
        current_width = current_row = current_column = 0
        layout = None
        grid = QtWidgets.QVBoxLayout()
        grid.setSpacing(self._spacing)
        grid.setContentsMargins(self._contentsMargins)

        if align_v[1] or align_v[2]:
            grid.addStretch()
        
        #Add each item to layouts inside the grid
        for item in self._itemOrder + [None]:
            item_data = self._itemList[item]
            item_data['current_column'] = current_column

            previous_width = current_width
            current_width += item_data['width'] + self._spacing
            item_type = item_data['type']
            current_column += 1

            #Add the row to the grid
            if item is None or current_width > max_width and layout is not None:
                if align_h[0] or align_h[1]:
                    layout.addStretch()
                grid.addLayout(layout)
                layout = None

            #Create a new row
            if item is not None and layout is None:
                current_width = item_data['width']
                layout = QtWidgets.QHBoxLayout()
                layout.setSpacing(self._spacing)
                layout.setContentsMargins(0, 0, 0, 0)
                layout.setAlignment(QtCore.Qt.AlignLeft)
                layout.alignment()

                current_row += 1
                current_column = 0

                if align_h[1] or align_h[2]:
                    layout.addStretch()

            #Add item to layout
            if item_type == self.TYPE_WIDGET:
                layout.addWidget(item)
            elif item_type == self.TYPE_LAYOUT:
                layout.addLayout(item)
            item_data['current_row'] = current_row
        
        if align_v[0] or align_v[1]:
            grid.addStretch()

        #Assign the grid to a widget, then the widget to the QScrollArea
        temp_widget = QtWidgets.QWidget()
        temp_widget.setLayout(grid)
        self.setWidget(temp_widget)
    
    def resizeEvent(self, event=None):
        super(AutoGrid, self).resizeEvent(event)
        self.buildLayout()

    def setZoomSpeed(self, value):
        self._zoomSpeed = max(0, value / 10)
    
    def zoomSpeed(self):
        return self._zoomSpeed

    def wheelEvent(self, event):
        """Control zooming in and out if CTRL is pressed."""
        modifiers = QtWidgets.QApplication.keyboardModifiers()
        if modifiers & QtCore.Qt.ControlModifier:
            delta = event.delta()
            zoom_speed = self.zoomSpeed() + 1
            if delta > 0:
                grid_size = self._gridSize * zoom_speed
            else:
                grid_size = self._gridSize / zoom_speed
            self.setGridSize(grid_size)
        else:
            super(AutoGrid, self).wheelEvent(event)

    def setMaximumItemWidth(self, width=None):
        """Set a maximum width so that nothing exceeds it.
        This function will be re-run each time a new widget is added.
        """
        self._maximumItemWidth = width
        if width is None:
            self._maximumItemAdjustedHeight = None
        else:
            if self._maxAspect:
                max_height = width / self._maxAspect
                self._maximumItemAdjustedHeight = max_height
            else:
                self._maximumItemAdjustedHeight = None
        
        #Recalculate height if changed
        if self._widgetReady and self._maximumItemAdjustedHeight is not None and self._maximumItemAdjustedHeight < self._gridSize:
            self.setGridSize(self._maximumItemAdjustedHeight)

    def maximumItemWidth(self):
        return self._maximumItemWidth

    def setMaximumItemHeight(self, height=None):
        """Set a maximum height so that nothing exceeds it."""
        self._maximumItemHeight = height
        if self._widgetReady and self._maximumItemHeight is not None and self._maximumItemHeight < self._gridSize:
            self.setGridSize(self._maximumItemHeight)

    def maximumItemHeight(self):
        return self._maximumItemHeight

    def setMinimumItemWidth(self, width=None):
        """Set a minimum width so that nothing exceeds it.
        This function will be re-run each time a new widget is added.
        """
        self._minimumItemWidth = width
        if width is None:
            self._minimumItemAdjustedHeight = None
        else:
            if self._maxAspect:
                min_height = width / self._maxAspect
                self._minimumItemAdjustedHeight = min_height
            else:
                self._minimumItemAdjustedHeight = None

    def minimumItemWidth(self):
        return self._minimumItemWidth

    def setMinimumItemHeight(self, height=None):
        """Set a minimum height so that nothing exceeds it."""
        self._minimumItemHeight = height
        if self._widgetReady and self._minimumItemHeight is not None and self._minimumItemHeight > self._gridSize:
            self.setGridSize(self._minimumItemHeight)
    
    def minimumItemHeight(self):
        return self._minimumItemHeight

    def removeItem(self, item):
        if item in self._itemList:
            del self._itemList[item]
            del self._itemOrder[self._itemOrder.index(item)]
    
    def removeWidget(self, widget):
        self.removeItem(widget)
    
    def removeLayout(self, layout):
        self.removeItem(layout)

    def index(self, index):
        return self._itemOrder[index]

    def indexOf(self, item):
        return self._itemOrder.index(item)

    def row(self, row):
        return [item for item in self._itemList.values() if item['current_row'] == row]

    def rowOf(self, item):
        return self._itemList[item]['current_row']

    def column(self, column):
        return [item for item in self._itemList.values() if item['current_column'] == column]

    def columnOf(self, item):
        return self._itemList[item]['current_column']