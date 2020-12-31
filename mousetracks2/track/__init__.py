import time
from functools import partial
from queue import Empty

from constants import *
from utils import (DOUBLE_CLICK_INTERVAL,
                   cursor_position, get_monitor_locations, check_key_press)


class MainThread(object):
    """Main tracking script.
    This runs in realtime and sends data to a background thread for
    processing, and also handles the communication with the GUI.
    """

    def __init__(self, gui=None, ups=60):
        """Setup the tracking thread.

        Parameters:
            gui (QObject): The main GUI.
            ups (int): The number of updates per second.
        """
        self.gui = gui
        self.ups = ups
        self.start()

        self.double_click_ticks = int(round(self.ups * DOUBLE_CLICK_INTERVAL))

        # Map commands to functions
        self.mapping_important = {
            GUICommand.Stop: self.stop,
            GUICommand.Pause: partial(self.pause, True),
            GUICommand.Unpause: partial(self.pause, False),
            GUICommand.TogglePause: self.pause,
        }
        self.mapping_pausable = {
            GUICommand.RaiseException: lambda: 1/0,
        }

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, state):
        try:
            old_state = self._state
        except AttributeError:
            old_state = ThreadState.Stopped
        self._state = state
        if old_state != state:
            print(f'Thread state changed: {state.name}')

    def send_event(self, event, *args, **kwargs):
        """Send an event back to the GUI.

        Parameters:
            event (ThreadEvent): Event to send to the GUI.
        """
        if self.gui is None:
            return
        if not isinstance(event, ThreadEvent):
            event = ThreadEvent[event]
        self.gui.receiveFromThread(event, *args, **kwargs)

    def start(self):
        """Mark the script as started."""
        self.pause(False)
        self.state = ThreadState.Running
        self.send_event(ThreadEvent.Started)

    def stop(self):
        """Mark the script as stopped."""
        self.state = ThreadState.Stopped
        self.send_event(ThreadEvent.Stopped)

    def pause(self, pause=None):
        """Pause or unpause the processing of events.
        When paused, events will be received but ignored.

        Parameters:
            pause (bool): If the script should be paused or not.
                If None, it will reverse the existing value.
                Default: None
        """
        if pause is None:
            try:
                pause = self.state != ThreadState.Paused
            except AttributeError:
                pause = True

        if pause:
            self.state = ThreadState.Paused
            self.send_event(ThreadEvent.Paused)
        else:
            self.state = ThreadState.Running
            self.send_event(ThreadEvent.Unpaused)

    def run(self):
        """Main loop to do all the realtime processing."""
        check_monitors_interval = 1
        check_monitors_override = False

        old_mouse_pos = old_monitors = None
        old_monitor_index = monitor_index = None
        keys = {item: [0] * 255 for item in ('tick', 'prev', 'count', 'held')}
        ticks = 0
        start = time.time()
        while self.state != ThreadState.Stopped:
            # Handle any GUI commands
            if self.gui is not None:
                while self.gui.queue:
                    command = self.gui.queue.pop(0)

                    # Commands that must be executed
                    if command in self.mapping_important:
                        self.mapping_important[command]()

                    # Commands that may only run if not paused
                    elif command in self.mapping_pausable:
                        if self.state != ThreadState.Paused:
                            self.mapping_pausable[command]()

            # Handle realtime data
            if self.state == ThreadState.Running:
                # Get mouse data
                mouse_pos = cursor_position()
                mouse_moved = mouse_pos != old_mouse_pos

                # Get monitor data
                if not ticks % check_monitors_interval or check_monitors_override:
                    check_monitors_override = False
                    monitors = get_monitor_locations()
                    monitors_changed = monitors != old_monitors

                # Get keyboard/mouse clicks
                # Note this will not see anything faster than 1/60th of a second
                for key, val in enumerate(keys['tick']):
                    previously_pressed = bool(val)
                    currently_pressed = bool(check_key_press(key))

                    # Detect individual key releases
                    if previously_pressed and not currently_pressed:
                        print(f'Key/button released: {key}')
                        keys['tick'][key] = keys['held'][key] = 0

                    # Detect when a key is being held down
                    elif previously_pressed and currently_pressed:
                        keys['held'][key] += 1
                        print(f'Key/button held: {key}')

                    # Detect when a new key is pressed
                    elif not previously_pressed and currently_pressed:
                        print(f'Key/button pressed: {key}')

                        # Figure out if a double click happened
                        if ticks - keys['prev'][key] < self.double_click_ticks:
                            keys['count'][key] += 1
                            print(f'Presses detected: {keys["count"][key]}')
                        else:
                            keys['count'][key] = 1
                        keys['tick'][key] = keys['prev'][key] = ticks

                # Check mouse data against monitors
                if mouse_pos is None:  # Cancel if there is no mouse data
                    refresh_monitor_index = False
                elif monitor_index is None:  # If index hasn't been set yet
                    refresh_monitor_index = True
                elif mouse_moved or monitors_changed:  # If there's been any changes
                    refresh_monitor_index = True
                else:
                    refresh_monitor_index = False
                if refresh_monitor_index:
                    mx, my = mouse_pos
                    for i, (x1, y1, x2, y2) in enumerate(monitors):
                        if x1 <= mouse_pos[0] < x2 and y1 <= mouse_pos[1] < y2:
                            # Keep track of which monitor the mouse is on
                            monitor_index = i

                            # Remap mouse position to be within 0 and 1
                            # This is for the GUI "live" preview only
                            remapped = (
                                (mouse_pos[0] - x1) / (x2 - x1),
                                (mouse_pos[1] - y1) / (y2 - y1),
                            )
                            self.send_event(ThreadEvent.MouseMove, remapped)
                            break

                    # If this part fails, monitors may have changed since being recorded
                    else:
                        print(
                          f'Unknown monitor detected (mouse: {mouse_pos}, saved: '
                          f'{monitors}, actual: {get_monitor_locations()}'
                        )
                        check_monitors_override = True
                        monitor_index = None
                        continue
                mouse_monitor_changed = monitor_index != old_monitor_index

                if mouse_monitor_changed:
                    vres = monitors[monitor_index][3] - monitors[monitor_index][1]
                    print(f'Mouse moved to {vres}p monitor')
                if mouse_moved:
                    print(f'Mouse moved: {mouse_pos}')

                # Store old values
                old_mouse_pos = mouse_pos
                old_monitors = monitors
                old_monitor_index = monitor_index

            # Ensure loop is running at the correct UPS
            ticks += 1
            time_expected = ticks / self.ups
            time_diff = time.time() - start
            if time_expected > time_diff:
                time.sleep(time_expected - time_diff)


def run(gui):
    """Execute the main loop and catch any errors."""
    main = MainThread(gui)

    try:
        main.run()
    except BaseException:
        main.send_event(ThreadEvent.Exception)
        raise
