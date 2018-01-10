"""
This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""
#Create a basic tray icon to perform simple API commands
#Lightly modified from a mix of win32gui_taskbar and http://www.brunningonline.net/simon/blog/archives/SysTrayIcon.py.html

from __future__ import absolute_import

import pywintypes
import win32api
import win32gui
import win32con
import win32gui_struct
import winerror
import win32ui
import sys
import os
from future.utils import iteritems
from multiprocessing import freeze_support


def non_string_iterable(obj):
    try:
        iter(obj)
    except TypeError:
        return False
    else:
        return not isinstance(obj, basestring)


class Tray:
    QUIT = 'QUIT'
    SPECIAL_ACTIONS = [QUIT]

    FIRST_ID = 1023

    def __init__(self, menu_options):
    
        self._refresh_menu(menu_options)
    
        msg_TaskbarRestart = win32gui.RegisterWindowMessage("TaskbarCreated");
        message_map = {
            msg_TaskbarRestart: self.OnRestart,
            win32con.WM_DESTROY: self.OnDestroy,
            win32con.WM_COMMAND: self.OnCommand,
            win32con.WM_USER+20: self.OnTaskbarNotify,
        }
        # Register the Window class.
        wc = win32gui.WNDCLASS()
        hinst = wc.hInstance = win32api.GetModuleHandle(None)
        wc.lpszClassName = "PythonTaskbarDemo"
        wc.style = win32con.CS_VREDRAW | win32con.CS_HREDRAW;
        wc.hCursor = win32api.LoadCursor(0, win32con.IDC_ARROW)
        wc.hbrBackground = win32con.COLOR_WINDOW
        wc.lpfnWndProc = message_map # could also specify a wndproc.

        # Don't blow up if class already registered to make testing easier
        try:
            classAtom = win32gui.RegisterClass(wc)
        except win32gui.error, err_info:
            if err_info.winerror!=winerror.ERROR_CLASS_ALREADY_EXISTS:
                raise

        # Create the Window.
        style = win32con.WS_OVERLAPPED | win32con.WS_SYSMENU
        self.hwnd = win32gui.CreateWindow(wc.lpszClassName, "Taskbar Demo", style, \
                0, 0, win32con.CW_USEDEFAULT, win32con.CW_USEDEFAULT, \
                0, 0, hinst, None)
        win32gui.UpdateWindow(self.hwnd)
        self._DoCreateIcons()
        
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
            
            invalid = not kwargs
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
        
    def _refresh_menu(self, menu_options=None):
        """Recalculate the menu options."""
        if menu_options is None:
            menu_options = self._menu_options
        else:
            self._menu_options = list(menu_options)
            
        self._next_action_id = self.FIRST_ID
        self.menu_actions_by_id = {}
        self.menu_options = self._add_ids_to_menu_options(self._menu_options)
        del self._next_action_id
    
    def _add_ids_to_menu_options(self, menu_options):
        """Add internal IDs to the menu options."""
        result = []
        for menu_option in menu_options:
            option_text = menu_option.get('name')
            option_icon = menu_option.get('icon', None)
            option_action = menu_option.get('action', None)
            option_args = menu_option.get('args', [])
            option_kwargs = menu_option.get('kwargs', {})
            
            if isinstance(option_action, tuple):
                result.append({k: v for k, v in iteritems(menu_option) if k != 'action'})
                result[-1]['action'] = self._add_ids_to_menu_options(option_action)
                result[-1]['_id'] = self._next_action_id
            elif option_action is None:
                result.append(menu_option)
            else:
                self.menu_actions_by_id[self._next_action_id] = (option_action, option_args, option_kwargs)
                result.append(menu_option)
                result[-1]['_id'] = self._next_action_id
            
            '''
            if callable(option_action) or option_action in self.SPECIAL_ACTIONS:
                self.menu_actions_by_id[self._next_action_id] = (option_action, option_args, option_kwargs)
                result.append(menu_option)
                result[-1]['_id'] = self._next_action_id
                
            elif non_string_iterable(option_action):
                result.append({k: v for k, v in iteritems(menu_option) if k != 'action'})
                result[-1]['action'] = self._add_ids_to_menu_options(option_action)
                result[-1]['_id'] = self._next_action_id
            else:
                print 'Unknown item', option_text, option_icon, option_action
                '''
            self._next_action_id += 1
        return result

    def _DoCreateIcons(self):
        # Try and find a custom icon
        hinst =  win32api.GetModuleHandle(None)
        iconPathName = os.path.abspath(os.path.join( os.path.split(sys.executable)[0], "pyc.ico" ))
        if not os.path.isfile(iconPathName):
            # Look in DLLs dir, a-la py 2.5
            iconPathName = os.path.abspath(os.path.join( os.path.split(sys.executable)[0], "DLLs", "pyc.ico" ))
        if not os.path.isfile(iconPathName):
            # Look in the source tree.
            iconPathName = os.path.abspath(os.path.join( os.path.split(sys.executable)[0], "..\\PC\\pyc.ico" ))
        if os.path.isfile(iconPathName):
            icon_flags = win32con.LR_LOADFROMFILE | win32con.LR_DEFAULTSIZE
            hicon = win32gui.LoadImage(hinst, iconPathName, win32con.IMAGE_ICON, 0, 0, icon_flags)
        else:
            print "Can't find a Python icon file - using default"
            hicon = win32gui.LoadIcon(0, win32con.IDI_APPLICATION)

        flags = win32gui.NIF_ICON | win32gui.NIF_MESSAGE | win32gui.NIF_TIP
        nid = (self.hwnd, 0, flags, win32con.WM_USER+20, hicon, "Python Demo")
        try:
            win32gui.Shell_NotifyIcon(win32gui.NIM_ADD, nid)
        except win32gui.error:
            # This is common when windows is starting, and this code is hit
            # before the taskbar has been created.
            print "Failed to add the taskbar icon - is explorer running?"
            # but keep running anyway - when explorer starts, we get the
            # TaskbarCreated message.

    def OnRestart(self, hwnd, msg, wparam, lparam):
        self._DoCreateIcons()

    def OnDestroy(self, hwnd, msg, wparam, lparam):
        nid = (self.hwnd, 0)
        win32gui.Shell_NotifyIcon(win32gui.NIM_DELETE, nid)
        win32gui.PostQuitMessage(0) # Terminate the app.

    def OnTaskbarNotify(self, hwnd, msg, wparam, lparam):
        """Receive click events from the taskbar."""
        if lparam==win32con.WM_LBUTTONUP:
            print "You clicked me."
        elif lparam==win32con.WM_LBUTTONDBLCLK:
            print "You double-clicked me - goodbye"
            win32gui.DestroyWindow(self.hwnd)
        elif lparam==win32con.WM_RBUTTONUP:
            print "You right clicked me."
            self.show_menu()
        return 1

    def OnCommand(self, hwnd, msg, wparam, lparam):
        """Run functions from ID."""
        id = win32api.LOWORD(wparam)
        
        #Handle case when action isn't set
        try:
            action, args, kwargs = self.menu_actions_by_id[id]
        except KeyError:
            pass
        else:
            action(self, *args, **kwargs)

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

    def _create_menu(self, menu, menu_options):
        """Generate the popup menu just before drawing.
        This is needed as it recursively runs on submenus.
        """
        
        for menu_option in menu_options[::-1]:
        
            option_text = menu_option.get('name')
            option_icon = menu_option.get('icon', None)
            option_action = menu_option.get('action', None)
            option_id = menu_option.get('_id')
            
            if option_icon:
                try:
                    option_icon = self.prep_menu_icon(option_icon)
                except pywintypes.error:
                    option_icon = None
            
            if option_id in self.menu_actions_by_id or option_action is None:                
                item, extras = win32gui_struct.PackMENUITEMINFO(text=option_text,
                                                                hbmpItem=option_icon,
                                                                wID=option_id)
                win32gui.InsertMenuItem(menu, 0, 1, item)
            else:
                submenu = win32gui.CreatePopupMenu()
                self._create_menu(submenu, option_action)
                item, extras = win32gui_struct.PackMENUITEMINFO(text=option_text,
                                                                hbmpItem=option_icon,
                                                                hSubMenu=submenu)
                win32gui.InsertMenuItem(menu, 0, 1, item)
                
    def prep_menu_icon(self, icon):
        """Load icons into the tray.
        
        Got from https://stackoverflow.com/a/45890829
        """
        # First load the icon.
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

        return iconBitmap.GetHandle()


def start_program(menu_options):
    t = Tray(menu_options)
    win32gui.PumpMessages()


def quit(cls):
    """Quit the program."""
    win32gui.DestroyWindow(cls.hwnd)


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
        
        self.set_menu_item('it1', name='Item 3')
    menu_options = (
        {'id': 'it1', 'name': 'Item 1', 'icon': 'path/to/img.ico', 'action': print_input, 'args': [1, 2], 'kwargs': {'key': 'value'}},
        {'name': 'Increment First Item', 'action': increment_item, 'args': ['it1']},
        {'id': 'sm1', 'name': 'Submenu 1', 'icon': None, 'action': (
            {'id': 'it2', 'name': 'Item 2'},
        )},
        {'name': 'Quit', 'action': quit},
    )
    start_program(menu_options)