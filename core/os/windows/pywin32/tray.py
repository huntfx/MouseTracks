"""
This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""
#Create a basic tray icon to perform simple API commands
#Modified from a mix of win32gui_taskbar and http://www.brunningonline.net/simon/blog/archives/SysTrayIcon.py.html

from __future__ import absolute_import

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
from future.utils import iteritems
from multiprocessing import freeze_support


class Tray(object):
    """Create a tray program.
    Submenus can be used and any item can be modified.
    
    See at the bottom of the file for example usage.
    """
    FIRST_ID = 1023

    def __init__(self, menu_options, program_name='Python Taskbar', menu_open=None, menu_close=None, main_hwnd=None, _internal_class_name='PythonTaskbar'):
    
        self.on_menu_open = menu_open
        self.on_menu_close = menu_close
        self.program_name = program_name
        self._hwnd = win32console.GetConsoleWindow()
        self._refresh_menu(menu_options)
    
        msg_TaskbarRestart = win32gui.RegisterWindowMessage('TaskbarCreated');
        message_map = {
            msg_TaskbarRestart: self.OnRestart,
            win32con.WM_DESTROY: self.OnDestroy,
            win32con.WM_COMMAND: self.OnCommand,
            win32con.WM_USER+20: self.OnTaskbarNotify,
        }
        # Register the Window class.
        wc = win32gui.WNDCLASS()
        hinst = wc.hInstance = win32api.GetModuleHandle(None)
        wc.lpszClassName = _internal_class_name
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

        #Create the Window.
        style = win32con.WS_OVERLAPPED | win32con.WS_SYSMENU
        self.hwnd = win32gui.CreateWindow(wc.lpszClassName, _internal_class_name, style, \
                0, 0, win32con.CW_USEDEFAULT, win32con.CW_USEDEFAULT, \
                0, 0, hinst, None)
        win32gui.UpdateWindow(self.hwnd)
        self._set_icon()

    def OnRestart(self, hwnd, msg, wparam, lparam):
        self._set_icon()

    def OnDestroy(self, hwnd, msg, wparam, lparam):
        nid = (self.hwnd, 0)
        win32gui.Shell_NotifyIcon(win32gui.NIM_DELETE, nid)
        win32gui.PostQuitMessage(0) # Terminate the app.

    def OnTaskbarNotify(self, hwnd, msg, wparam, lparam):
        """Receive click events from the taskbar."""
        
        #Left click
        if lparam==win32con.WM_LBUTTONUP:
            pass
            
        #Double click (minimise/maximise)
        elif lparam==win32con.WM_LBUTTONDBLCLK:
            if win32gui.IsIconic(self._hwnd):
                win32gui.ShowWindow(self._hwnd, win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(self._hwnd)
            else:
                win32gui.ShowWindow(self._hwnd, win32con.SW_MINIMIZE)
                
                #Hide window
                win32gui.ShowWindow(self._hwnd, win32con.SW_HIDE)
                win32gui.SetWindowLong(self._hwnd, win32con.GWL_EXSTYLE,
                                       win32gui.GetWindowLong(self._hwnd, win32con.GWL_EXSTYLE) | win32con.WS_EX_TOOLWINDOW);
                win32gui.ShowWindow(self._hwnd, win32con.SW_SHOW);
        
        #Right click (load menu)
        elif lparam==win32con.WM_RBUTTONUP:
            if self.on_menu_open is not None:
                self.on_menu_open(self)
            self.show_menu()
            if self.on_menu_close is not None:
                self.on_menu_close(self)
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

    def _set_icon(self, icon_path=None):
        """Load the tray icon.
        Doesn't appear to be editable once it's been set.
        """
        
        #Try and find a custom icon
        if icon_path is None:
            icon_path = os.path.abspath(os.path.join(os.path.split(sys.executable)[0], 'pyc.ico'))
        
            #Look in DLLs dir
            if not os.path.isfile(icon_path):
                icon_path = os.path.abspath(os.path.join(os.path.split(sys.executable)[0], 'DLLs', 'pyc.ico'))
            
            #Look in the source tree
            if not os.path.isfile(icon_path):
                icon_path = os.path.abspath(os.path.join(os.path.split(sys.executable)[0], '..\\PC\\pyc.ico'))
        
        #Load icon as an image
        try:
            if not os.path.isfile(icon_path):
                raise TypeError
            icon_flags = win32con.LR_LOADFROMFILE | win32con.LR_DEFAULTSIZE
            hinst = win32api.GetModuleHandle(None)
            hicon = win32gui.LoadImage(hinst, icon_path, win32con.IMAGE_ICON, 0, 0, icon_flags)
        
        #Fallback to default windows icon
        except TypeError:
            hicon = win32gui.LoadIcon(0, win32con.IDI_APPLICATION)
        
        flags = win32gui.NIF_ICON | win32gui.NIF_MESSAGE | win32gui.NIF_TIP
        nid = (self.hwnd, 0, flags, win32con.WM_USER+20, hicon, self.program_name)
        try:
            win32gui.Shell_NotifyIcon(win32gui.NIM_ADD, nid)
        except win32gui.error:
            # This is common when windows is starting, and this code is hit
            # before the taskbar has been created.
            # but keep running anyway - when explorer starts, we get the
            # TaskbarCreated message.
            pass
                
    def _set_icon_menu(self, icon):
        """Load icons into the tray items.
        
        Got from https://stackoverflow.com/a/45890829
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
        #pywintypes.error: (0, 'SetForegroundWindow', 'No error message is available')
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
        
            if menu_option.get('hidden', False):
                continue
        
            text = menu_option.get('name', 'Option')
            icon = menu_option.get('icon', None)
            action = menu_option.get('action', None)
            id = menu_option.get('_id')
            
            if icon:
                try:
                    icon = self._set_icon_menu(icon)
                except pywintypes.error:
                    icon = None
            
            if id in self.menu_actions_by_id or action is None:                
                item, extras = win32gui_struct.PackMENUITEMINFO(text=text,
                                                                hbmpItem=icon,
                                                                wID=id)
                win32gui.InsertMenuItem(menu, 0, 1, item)
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