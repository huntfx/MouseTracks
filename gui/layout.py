"""This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""

from __future__ import absolute_import

from core.qt import *
from ext.Qt import QtWidgets, QtCore

class MainWindowLayout(object):
    def setup(self, MainWindow):
        with QtVResizableLayout(MainWindow) as draggable_layout:
            with QtLayout(QtWidgets.QHBoxLayout, draggable_layout) as program_layout:
                program_layout.spacing = 6
                program_layout.margins = 0
                program_layout.add_label('this is text')
                with QtTabGroupLayout(program_layout, fixed_width=278) as tab_group:
                    with QtTabCombined(QtWidgets.QVBoxLayout, tab_group, 'Render Options') as (tab_widget, tab_layout):
                        with QtScrollZoneCombined(QtWidgets.QVBoxLayout, tab_layout) as (scroll_area, scroll_layout):
                            
                            with QBoxGroup(scroll_layout, 'Profile Selection') as group_layout:
                                with QtLayout(QtWidgets.QVBoxLayout, group_layout) as group_parts:
                                    group_parts.add_dropdown(['<current>', 'Default', 'Overwatch', 'Path of Exile'])
                                    
                            with QBoxGroup(scroll_layout, 'Image Options') as group_layout:
                                with QtLayout(QtWidgets.QVBoxLayout, group_layout) as group_parts:
                                    group_parts.add_dropdown(['Tracks', 'Clicks', 'Acceleration', 'Keyboard'])
                                    group_parts.add_dropdown(['Time', 'Count'], visible=False)
                                    
                            with QBoxGroup(scroll_layout, 'Colour Options') as group_layout:
                                with QtLayout(QtWidgets.QVBoxLayout, group_layout) as group_parts:
                                    with QtLayout(QtWidgets.QHBoxLayout, group_parts) as group_line:
                                        group_line.add_textfield('Demon')
                                        group_line.add_dropdown(['Presets', 'Citrus', 'Demon', 'Sunburst'])
                                    
                            with QBoxGroup(scroll_layout, 'Saving') as group_layout:
                                with QtLayout(QtWidgets.QVBoxLayout, group_layout) as group_parts:
                                    group_parts.add_checkbox('Limit to current session')
                                    with QtLayout(QtWidgets.QHBoxLayout, group_parts) as group_line:
                                        group_line.add_button('Save Image')
                                        group_line.add_stretch()
                                        group_line.add_button('Export Data')
                                    
                            with QBoxGroup(scroll_layout, 'Show/Hide Mouse Buttons') as group_layout:
                                with QtLayout(QtWidgets.QVBoxLayout, group_layout) as group_parts:
                                    group_parts.add_checkbox('Left Mouse Button')
                                    group_parts.add_checkbox('Middle Mouse Button')
                                    group_parts.add_checkbox('Right Mouse Button')
                                    
                    with QtTabCombined(QtWidgets.QVBoxLayout, tab_group, 'Advanced') as (tab_widget, tab_layout):
                        with QtScrollZoneCombined(QtWidgets.QVBoxLayout, tab_layout) as (scroll_area, scroll_layout):
                            
                            with QBoxGroup(scroll_layout, 'Custom Tracking Groups') as group_layout:
                                with QtLayout(QtWidgets.QVBoxLayout, group_layout) as group_parts:
                                    with QtLayout(QtWidgets.QHBoxLayout, group_parts) as group_line:
                                        group_line.add_textfield('<Default>')
                                        group_line.add_button('Apply')
                                    group_parts.add_checkbox('Set as default for current profile')
                                    group_parts.add_checkbox('Keep this group active on profile switch')
                                    group_parts.add_checkbox('Disable profile switching')
                                        
                            scroll_layout.add_stretch()
            draggable_layout.add_list(['test'])

    def closeEvent(self, event):
        print(5)
        exit()