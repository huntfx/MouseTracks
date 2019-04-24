"""This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""
#Create a basic tray icon to perform API commands
#Modified from a mix of win32gui_taskbar and http://www.brunningonline.net/simon/blog/archives/SysTrayIcon.py.html

from __future__ import absolute_import

import logging
import os
import pywintypes
import sys
import win32api
import win32gui
import win32con
import win32console
import win32gui_struct
import winerror
import win32ui
from multiprocessing import freeze_support

from .main import WindowHandle
from ....compatibility import callable, iteritems


TRAY_EVENT = win32con.WM_USER + 20


class Tray(object):
    """Create a tray program.
    Submenus can be used and any item can be modified.
    
    See at the bottom of the file for example usage.
    """
    FIRST_ID = 1023

    def __init__(self, menu_options, program_name='Python Taskbar', window_name=None):

        self.logger = logging.getLogger("tray")
        self.cache = {}
        self._commands = {'OnMenuOpen': [],
                          'OnMenuClose': [],
                          'OnWindowHide': [],
                          'OnWindowRestore': []}
        self.program_name = program_name
        try:
            self.console_hwnd = WindowHandle(parent=False, console=True)
        except NameError:
            self.console_hwnd = None
        self._refresh_menu(menu_options)
        if window_name is None:
            window_name = program_name

        #Set up callbacks
        msg_TaskbarRestart = win32gui.RegisterWindowMessage('TaskbarCreated')
        message_map = {
            msg_TaskbarRestart: self.OnRestart,
            win32con.WM_DESTROY: self.OnDestroy,
            win32con.WM_COMMAND: self.OnCommand,
            TRAY_EVENT: self.OnTaskbarNotify,
        }
        #Register the Window class.
        wc = win32gui.WNDCLASS()
        hinst = wc.hInstance = win32api.GetModuleHandle(None)
        wc.lpszClassName = window_name
        wc.style = win32con.CS_VREDRAW | win32con.CS_HREDRAW
        wc.hCursor = win32api.LoadCursor(0, win32con.IDC_ARROW)
        wc.hbrBackground = win32con.COLOR_WINDOW
        wc.lpfnWndProc = message_map # could also specify a wndproc.

        #Don't blow up if class already registered to make testing easier
        try:
            classAtom = win32gui.RegisterClass(wc)
        except (win32gui.error, err_info):
            if err_info.winerror!=winerror.ERROR_CLASS_ALREADY_EXISTS:
                raise

        #Create the Window.
        style = win32con.WS_OVERLAPPED | win32con.WS_SYSMENU
        self.hwnd = win32gui.CreateWindow(wc.lpszClassName, window_name, style, \
                0, 0, win32con.CW_USEDEFAULT, win32con.CW_USEDEFAULT, \
                0, 0, hinst, None)
        win32gui.UpdateWindow(self.hwnd)
        self._set_icon()
        self.logger.info('Window created.')

    def OnRestart(self, hwnd, msg, wparam, lparam):
        self.logger.info('Window restarted.')
        self._set_icon()

    def OnDestroy(self, hwnd, msg, wparam, lparam):
        nid = (self.hwnd, 0)
        win32gui.Shell_NotifyIcon(win32gui.NIM_DELETE, nid)
        win32gui.PostQuitMessage(0)
        self.logger.info('Window destroyed.')

    def OnTaskbarNotify(self, hwnd, msg, wparam, lparam):
        """Receive click events from the taskbar."""
        
        #Left click
        if lparam==win32con.WM_LBUTTONUP:
            pass
            
        #Double click (bring to front)
        elif lparam==win32con.WM_LBUTTONDBLCLK:
            
            always_bring_to_front = True
            
            if always_bring_to_front or self.console_hwnd is not None and self.console_hwnd.minimised:
                self.logger.info('Double click to bring window to foreground.')
                self.bring_to_front()
            else:
                self.logger.info('Double click to minimise window.')
                self.minimise_to_tray()
        
        #Right click (load menu)
        elif lparam==win32con.WM_RBUTTONUP:
            self.logger.info('Right click to open menu.')

            for func in self._commands['OnMenuOpen']:
                self.logger.debug('Called "%s" after opening menu.', func.__name__)
                func(self)
            
            #Occasionally the menu may fail to load for some reason, so skip
            try:
                self.show_menu()
            except pywintypes.error:
                return 0
                
            for func in self._commands['OnMenuClose']:
                self.logger.debug('Called "%s" after closing menu.', func.__name__)
                func(self)
        return 1

    def OnCommand(self, hwnd, msg, wparam, lparam):
        """Run functions from ID."""
        id = win32api.LOWORD(wparam)
        
        #Handle case when action isn't set
        try:
            action, args, kwargs = self.menu_actions_by_id[id]
            self.logger.info('Function "%s" was called.', action.__name__)
        except KeyError:
            pass
        else:
            action(self, *args, **kwargs)

    def set_event(self, trigger, *args):
        """Set which functions to run for certain events.
        
        Currently supported:
            OnMenuOpen
            OnMenuClose
            OnWindowHide
            OnWindowRestore
        """
        if trigger not in self._commands:
            return
        valid_functions = []
        for func in args:
            if callable(func):
                valid_functions.append(func)
                self.logger.info('Registered "%s" for trigger "%s".', func.__name__, trigger)
            else:
                try:
                    self.logger.warning('Failed to register "%s" for trigger "%s".', func.__name__, trigger)
                except AttributeError:
                    self.logger.warning('Failed to register "%s" for trigger "%s".', str(func), trigger)
        self._commands[trigger] = valid_functions

        
    def minimise_to_tray(self):
        """Remove the console window.
        A minimised window can't be hidden to tray, so restore it first.
        """
        if self.console_hwnd is None:
            return

        if self.console_hwnd.minimised:
            self.console_hwnd.restore()
            
        self.console_hwnd.hide()
        for func in self._commands['OnWindowHide']:
            func(self)
        
        if self.__dict__.get('minimise_override', None):
            del self.minimise_override
            self.bring_to_front()

        self.logger.info('Window hidden.')
            
    def bring_to_front(self):
        """Bring the console window to the front."""
        if self.console_hwnd is None:
            return

        if self.__dict__.get('minimise_override', None):
            del self.minimise_override
            self.minimise_to_tray()
        self.console_hwnd.bring_to_front()
        
        for func in self._commands['OnWindowRestore']:
            func(self)

        self.logger.info('Window restored.')
            
    def _set_icon(self, icon_path=None):
        """Load the tray icon.

        Doesn't appear to be editable once it's been set.
        TODO: Look at http://www.brunningonline.net/simon/blog/archives/SysTrayIcon.py.html on how to edit it.
        """

        #Load icon as an image
        try:
            if icon_path is None or not os.path.isfile(icon_path):
                raise TypeError
            icon_flags = win32con.LR_LOADFROMFILE | win32con.LR_DEFAULTSIZE
            hinst = win32api.GetModuleHandle(None)
            hicon = win32gui.LoadImage(hinst, icon_path, win32con.IMAGE_ICON, 0, 0, icon_flags)
        
        #Fallback to default windows icon
        except TypeError:
            hicon = win32gui.LoadIcon(0, win32con.IDI_APPLICATION)
        
        flags = win32gui.NIF_ICON | win32gui.NIF_MESSAGE | win32gui.NIF_TIP
        nid = (self.hwnd, 0, flags, TRAY_EVENT, hicon, self.program_name)
        try:
            win32gui.Shell_NotifyIcon(win32gui.NIM_ADD, nid)
        except win32gui.error:
            # This is common when windows is starting, and this code is hit
            # before the taskbar has been created.
            # but keep running anyway - when explorer starts, we get the
            # TaskbarCreated message.
            pass

        self.logger.debug('Set tray icon.')
                
    def _set_icon_menu(self, icon):
        """Load icons into the tray items.
        
        Got from https://stackoverflow.com/a/45890829.
        """
        ico_x = win32api.GetSystemMetrics(win32con.SM_CXSMICON)
        ico_y = win32api.GetSystemMetrics(win32con.SM_CYSMICON)
        hIcon = win32gui.LoadImage(0, icon, win32con.IMAGE_ICON, ico_x, ico_y, win32con.LR_LOADFROMFILE)

        hwndDC = win32gui.GetWindowDC(self.hwnd)
        dc = win32ui.CreateDCFromHandle(hwndDC)
        memDC = dc.CreateCompatibleDC()
        iconBitmap = win32ui.CreateBitmap()
        iconBitmap.CreateCompatibleBitmap(dc, ico_x, ico_y)
        oldBmp = memDC.SelectObject(iconBitmap)
        brush = win32gui.GetSysColorBrush(win32con.COLOR_MENU)

        win32gui.FillRect(memDC.GetSafeHdc(), (0, 0, ico_x, ico_y), brush)
        win32gui.DrawIconEx(memDC.GetSafeHdc(), 0, 0, hIcon, ico_x, ico_y, 0, 0, win32con.DI_NORMAL)

        memDC.SelectObject(oldBmp)
        memDC.DeleteDC()
        win32gui.ReleaseDC(self.hwnd, hwndDC)

        self.logger.debug('Set menu icon.')

        return iconBitmap.GetHandle()
        
    def _refresh_menu(self, menu_options=None):
        """Recalculate the menu options."""
        #Redraw from original or set new original
        if menu_options is None:
            menu_options = self._menu_options
        else:
            self._menu_options = list(menu_options)
        
        #Assign the IDs
        self._next_action_id = self.FIRST_ID
        self.menu_actions_by_id = {}
        self.menu_options = self._add_ids_to_menu_options(self._menu_options)
        del self._next_action_id
    
    def _add_ids_to_menu_options(self, menu_options):
        """Add internal IDs to menu options."""
        result = []
        for menu_option in menu_options:
            action = menu_option.get('action', None)
            
            #Submenu
            if isinstance(action, tuple):
                result.append({k: v for k, v in iteritems(menu_option) if k != 'action'})
                result[-1]['action'] = self._add_ids_to_menu_options(action)
                result[-1]['_id'] = self._next_action_id
                
            #No action provided
            elif action is None:
                result.append(menu_option)
                
            #Function
            else:
                args = menu_option.get('args', [])
                kwargs = menu_option.get('kwargs', {})
                self.menu_actions_by_id[self._next_action_id] = (action, args, kwargs)
                result.append(menu_option)
                result[-1]['_id'] = self._next_action_id
            self._next_action_id += 1
            
        return result

    def show_menu(self):
        """Draw the popup menu."""
        menu = win32gui.CreatePopupMenu()
        self._create_menu(menu, self.menu_options)
        
        pos = win32gui.GetCursorPos()
        # See http://msdn.microsoft.com/library/default.asp?url=/library/en-us/winui/menus_0hdi.asp
        win32gui.SetForegroundWindow(self.hwnd)
        win32gui.TrackPopupMenu(menu,
                                win32con.TPM_LEFTALIGN,
                                pos[0],
                                pos[1],
                                0,
                                self.hwnd,
                                None)
        win32gui.PostMessage(self.hwnd, win32con.WM_NULL, 0, 0)
        self.logger.debug('Menu displayed.')

    def _create_menu(self, menu, menu_options):
        """Generate the popup menu just before drawing.
        This is needed as it recursively runs on submenus.
        """
        
        for menu_option in menu_options[::-1]:
            if menu_option.get('hidden', False):
                continue
        
            text = menu_option.get('name', 'Option')
            icon = menu_option.get('icon', None)
            action = menu_option.get('action', None)
            id = menu_option.get('_id')
            
            #Set icon
            if icon:
                try:
                    icon = self._set_icon_menu(icon)
                except pywintypes.error:
                    icon = None
            
            #Add menu item
            if id in self.menu_actions_by_id or action is None:                
                item, extras = win32gui_struct.PackMENUITEMINFO(text=text,
                                                                hbmpItem=icon,
                                                                wID=id)
                win32gui.InsertMenuItem(menu, 0, 1, item)
            
            #Add submenu
            else:
                submenu = win32gui.CreatePopupMenu()
                self._create_menu(submenu, action)
                item, extras = win32gui_struct.PackMENUITEMINFO(text=text,
                                                                hbmpItem=icon,
                                                                hSubMenu=submenu)
                win32gui.InsertMenuItem(menu, 0, 1, item)
        
    def set_menu_item(self, menu_id, _menu_options=None, **kwargs):
        """Change a menu item where the ID matches the input."""
        if _menu_options is None:
            menu_options = self._menu_options
        else:
            menu_options = _menu_options
        
        for i, menu_option in enumerate(menu_options):
            #Get ID value, or skip if no ID
            id = menu_option.get('id', None)
            if id is None:
                continue
            
            #Update value if correct ID
            if id == menu_id:
                for k, v in iteritems(kwargs):
                    menu_options[i][k] = v
                self.logger.debug('Menu item "%s" updated (%s).', id, ', '.join('{}:"{}"'.format(k, v) for k, v in iteritems(kwargs)))
            
            #Look in submenu
            else:
                action = menu_option.get('action', None)
                if isinstance(action, tuple):
                    self.set_menu_item(menu_id, _menu_options=action, **kwargs)
        
        if _menu_options is None:
            self._refresh_menu(menu_options)

    def get_menu_item(self, _menu_options=None, **kwargs):
        """Return list of all items where the kwargs match."""
        if _menu_options is None:
            menu_options = self._menu_options
        else:
            menu_options = _menu_options
        
        matching_items = []
        for menu_option in menu_options:
            
            #Check if all kwargs match
            #Use "invalid = not kwargs" to fail when no kwargs are set,
            #otherwise all items will be returned by default
            invalid = False
            for k, v in iteritems(kwargs):
                try:
                    if menu_option[k] != v:
                        raise KeyError
                except KeyError:
                    invalid = True
                    break
            
            if not invalid:
                matching_items.append(menu_option)
            
            #Look in submenu
            action = menu_option.get('action', None)
            if isinstance(action, tuple):
                matching_items += self.get_menu_item(_menu_options=action, **kwargs)

        return matching_items

    def listen(self):
        """Run the tray program."""
        self.logger.info('Started listening for callbacks...')
        win32gui.PumpMessages()


def quit(cls):
    """Quit the program."""
    win32gui.DestroyWindow(cls.hwnd)


#Example usage
if __name__ == '__main__':

    def print_input(cls, *args, **kwargs):
        """Test that both args and kwargs have been sent."""
        print(args)
        print(kwargs)
        
    def increment_item(cls, id):
        """Rename "Item 1" to "Item x" where x is the lowest unused integer."""
        item = cls.get_menu_item(id=id)[0]
        name = item['name']
        last_int = int(name.split(' ')[1])
        while True:
            last_int += 1
            new_name = 'Item {}'.format(last_int)
            if not cls.get_menu_item(name=new_name):
                cls.set_menu_item(item['id'], name=new_name)
                print('Renamed {} to {}'.format(name, new_name))
                break
        
    menu_options = (
        {'id': 'it1', 'name': 'Item 1', 'icon': 'path/to/img.ico', 'action': print_input, 'args': [1, 2], 'kwargs': {'key': 'value'}},
        {'name': 'Increment First Item', 'action': increment_item, 'args': ['it1']},
        {'id': 'sm1', 'name': 'Submenu 1', 'icon': None, 'action': (
            {'id': 'it2', 'name': 'Item 2'},
        )},
        {'name': 'Quit', 'action': quit},
    )
    t = Tray(menu_options, 'My Taskbar')
    t.listen()