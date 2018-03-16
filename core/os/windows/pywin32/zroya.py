import threading
import logging
import os
import time

from win32api import GetModuleHandle
from win32con import *
from win32gui import *


class NotificationCenter(object):
    """
    Notification center is a hub for all created notifications. It handles events, runs callbacks etc.
    """

    NOTIFICATION_EVENT = WM_USER + 1  #: Event ID for all events associated with notifications.
    EVENT_BALLOON_SHOW = WM_USER + 2  #: Event ID fired when notification is created.
    EVENT_BALLOON_HIDE = WM_USER + 3 + 4  #: Event ID used when notification is hidden from code.
    EVENT_BALLOON_TIMEOUT = WM_USER + 4 + 2  #: Event ID for notification with expired timeout.
    EVENT_BALLOON_CLICK = WM_USER + 5  #: Event ID used when user clicks on notification.

    ICON_INFO = NIIF_INFO  #: This could be passed as icon parameter of create method. In this case, info icon is used.
    ICON_WARNING = NIIF_WARNING  #: This could be passed as icon parameter of create method. It will use warning icon.
    ICON_ERROR = NIIF_ERROR  #: This could be passed as icon parameter of create method. It will use error icon.

    def __init__(self):

        # List of all notifications. Each notification is represented by its ID (key) and thread (value).
        self._notifications = {}

        # Notification ID counter
        self._current_id = 0

        self.logger = logging.getLogger("zroya")

        # Event mapping. Keys is event type and value callback function.
        self._event_map = {
            WM_DESTROY: self.quit,
        }

        # Create window
        self._window_class = WNDCLASS()
        self._window_class.lpszClassName = str("Notification")
        self._window_class.lpfnWndProc = self._eventLoop
        self._class = RegisterClass(self._window_class)
        self._handle = GetModuleHandle(None)

        self._window = CreateWindow(self._class, "Notification", 0,
            0, 0, CW_USEDEFAULT, CW_USEDEFAULT, 0, 0, self._handle, None
        )

        # Draw window
        UpdateWindow(self._window)

        self.logger.debug("NotificationCenter created.")

    def quit(self):
        """
        Ends notification event loop.
        :returns: Nothing.
        """

        DestroyWindow(self._window)
        UnregisterClass(self._window_class.lpszClassName, None)
        PostQuitMessage(0)
        self.logger.debug("NotificationCenter is going to quit.")

    def update(self):
        """
        Polls all waiting events. This function should be called periodically in event loop. It polls all
        waiting events from queue and calls corresponding callbacks.
        :returns: False when notification center was shut down. True otherwise.
        """
        return PumpWaitingMessages() == 0

    def create(self, title, message, timeout = 0, icon=None, sound=True, on_click=None, on_show=None, on_hide=None,
        on_timeout=None
    ):
        """
        Shows notification. All callback functions take two parameters. First one is integer with notification ID,
        second is dict with parameters used for creation (title, message, icon).
        :param str          title:      Notification title.
        :param str          message:    Short notification text.
        :param int/float    timeout:    Number of seconds after which notification will be removed. This triggers on_timeout event.
        :param str/int      icon:       Path to the icon file or one of NotificationCenter.ICON_*. Use None for info icon.
        :param bool         sound:      Should sound be played when notification appears?
        :param callable     on_click:   On click callback. Called when user clicks on notification.
        :param callable     on_show:    On show callback. Called when notification is shown.
        :param callable     on_hide:    On hide callback. Called when notification is hidden from code.
        :param callable     on_timeout: On timeout callback. Called when notification timeout expires.
        :returns: Notification ID.
        """

        if not icon:
            icon = NotificationCenter.ICON_INFO

        # Add notification ID
        if self._current_id > 10 ** 6:
            # Count back from zero
            self._current_id = 0
            self.logger.debug("Maximum number of notification ID reached. Starting from zero again.")

        self._current_id += 1

        # Create thread with notification
        threading.Thread(target=self._create, kwargs={
            "window": self._window,
            "title": title,
            "message": message,
            "timeout": timeout,
            "notification_id": self._current_id,
            "icon_param": icon,
            "sound": sound,
            "logger": self.logger,
        }).start()

        self.logger.debug("Notification ID {} created.".format(self._current_id))

        # Create notification info.
        self._notifications[self._current_id] = {
            NotificationCenter.EVENT_BALLOON_CLICK: on_click,
            NotificationCenter.EVENT_BALLOON_SHOW: on_show,
            NotificationCenter.EVENT_BALLOON_HIDE: on_hide,
            NotificationCenter.EVENT_BALLOON_TIMEOUT: on_timeout,
            "data": {
                "title": title,
                "message": message,
                "icon": icon,
                "sound": sound,
            },
            "shown": False
        }

        return self._current_id

    def hide(self, notification_id, timeout = 0.0):
        """
        Remove notification with specific ID. If notification was not shown yet, return false. If **timeout** parameter
        is provided, function blocks for **timeout** seconds waiting for selected notification to be shown.
        :param int          notification_id:    ID of notification to hide.
        :param int/float    timeout:            Max waiting time for notification to ne shown.
        :return: True if notification was hidden, False otherwise.
        """

        # Ignore non-existing notifications
        if notification_id not in self._notifications:
            return False

        # Can not hide notification before it is shown
        if not self._notifications[notification_id]["shown"]:
            if timeout != 0:
                max_waiting_time = time.time() + timeout
                while time.time() < max_waiting_time:
                    if self._notifications[notification_id]["shown"]:
                        break
                    time.sleep(0.15)
            else:
                return False

        # Remove notification from system
        data = (self._window, notification_id)
        Shell_NotifyIcon(NIM_DELETE, data)

        # Trigger hide event
        PostMessage(self._window, NotificationCenter.NOTIFICATION_EVENT, notification_id, NotificationCenter.EVENT_BALLOON_HIDE)

    def _create(self, window, title, message, timeout, notification_id, logger, icon_param=None, sound=True):
        """
        Representation of notification thread.
        :param window: Window instance.
        :param title: Notification title.
        :param message: Notification text.
        :param timeout: Notification timeout.
        :param notification_id: Notification ID.
        :param icon_param: Notification icon path or one of NotificationCenter.ICON_*. Only .ICO and .BMP formats are
        supported.
        :returns: Nothing.
        """

        # Flags for notification
        flags = NIF_MESSAGE

        # Flags used for default icons (Error, Info, Warning) and no sound parameter.
        additional_flags = 0

        icon = None

        # Is path used?
        if icon_param:
            if type(icon_param) == str:
                flags |= NIF_ICON

                # Load icon from file
                try:
                    icon = LoadImage(
                        None,
                        icon_param,
                        IMAGE_ICON, 0, 0,
                        LR_LOADFROMFILE | LR_DEFAULTSIZE
                    )
                    logger.debug("Icon loaded for notification ID {}.".format(notification_id))

                except Exception as e:
                    # Use info icon as default
                    additional_flags |= NotificationCenter.ICON_INFO
                    logger.warning(
                        "Unable to load icon {} for notification ID {}. Using info icon instead. Error: {}"
                            .format(icon_param, notification_id, e)
                    )

            # Set one of predefined icons
            elif type(icon_param) == int:
                logger.debug("Using default icon {} for notification ID {}.".format(icon_param, notification_id))
                additional_flags |= icon_param

        else:
            logger.debug("Using default icon {} for notification ID {}.".format(icon_param, notification_id))
            additional_flags |= NotificationCenter.ICON_INFO

        # Disable sound effect
        if not sound:

            logger.debug("Sound effect disabled for notification ID {}.".format(notification_id))
            additional_flags |= NIIF_NOSOUND

        # Create tray icon notification
        nid = (window, notification_id, flags, NotificationCenter.NOTIFICATION_EVENT, icon, "Tooltip")
        Shell_NotifyIcon(NIM_ADD, nid)

        # Create notification
        Shell_NotifyIcon(NIM_MODIFY, (
            window, notification_id, NIF_INFO,
            NotificationCenter.NOTIFICATION_EVENT,
            icon,
            "Tooltip",
            message,
            0,
            title,
            additional_flags
        ))

        logger.debug("Notification ID {} created.".format(notification_id))

        if timeout > 0:
            time.sleep(timeout)
            Shell_NotifyIcon(NIM_DELETE, (window, notification_id))
            PostMessage(window, NotificationCenter.NOTIFICATION_EVENT, notification_id, NotificationCenter.EVENT_BALLOON_TIMEOUT)


    def _onNotificationEvent(self, notification_id, event_id):
        """
        Calls notification callback when needed.
        :param int  notification_id:    ID of notification which created event.
        :param int  event_id:           Event ID (one of NotificationCenter.EVENT_*.
        :return: Number one.
        """

        # Handle non-existing notification
        if notification_id not in self._notifications:
            self.logger.debug("Event fired for non-existing notification ID {}!".format(notification_id))
            return False

        # Get its data
        notification_data = self._notifications[notification_id]

        if event_id == NotificationCenter.EVENT_BALLOON_HIDE:
            self._onHideDefault(notification_id, notification_data)
        elif event_id == NotificationCenter.EVENT_BALLOON_SHOW:
            self._onShowDefault(notification_id, notification_data)
        elif event_id == NotificationCenter.EVENT_BALLOON_CLICK:
            self._onClickDefault(notification_id, notification_data)
        elif event_id == NotificationCenter.EVENT_BALLOON_TIMEOUT:
            self._onTimeoutDefault(notification_id, notification_data)

        return True

    def _onShowDefault(self, notification_id, notification_data):

        # Mark as shown
        self._notifications[notification_id]["shown"] = True

        # Is there user defined callback?
        callback = notification_data[NotificationCenter.EVENT_BALLOON_SHOW]
        if callback:
            # Call it
            callback(notification_id, notification_data)

    def _onHideDefault(self, notification_id, notification_data):

        # Is there user defined callback?
        callback = notification_data[NotificationCenter.EVENT_BALLOON_HIDE]
        if callback:
            # Call it
            callback(notification_id, notification_data)

        # Remove if from list
        self._notifications.pop(notification_id)

    def _onClickDefault(self, notification_id, notification_data):

        # Is there user defined callback?
        callback = notification_data[NotificationCenter.EVENT_BALLOON_HIDE]
        if callback:
            # Call it
            callback(notification_id, notification_data)

    def _onTimeoutDefault(self, notification_id, notification_data):

        PostMessage(self._window, NotificationCenter.NOTIFICATION_EVENT, notification_id, NotificationCenter.EVENT_BALLOON_HIDE)

        # Is there user defined callback?
        callback = notification_data[NotificationCenter.EVENT_BALLOON_TIMEOUT]
        if callback:
            # Call it
            callback(notification_id, notification_data)

        # Remove if from list
        self._notifications.pop(notification_id)

    def _eventLoop(self, window, event, w_param, l_param):
        """
        Custom representation of event loop. It separates events created within notifications and calls corresponding
        callbacks.
        :param window: Windows instance?
        :param int  event: Event type.
        :param int  w_param: First parameter. In case of notification event, it contains notification ID.
        :param int  l_param: Second parameter. In case of notification event, it contains event ID.
        :return: ??.
        """

        # Handle events for notifications
        if event == NotificationCenter.NOTIFICATION_EVENT:
            return self._onNotificationEvent(w_param, l_param)

        # Handle rest of the events
        return DefWindowProc(window, event, w_param, l_param)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.quit()

__ALL__ = ["NotificationCenter"]