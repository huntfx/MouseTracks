import time
from collections import defaultdict
from functools import partial
from queue import Empty

from constants import *
from utils import (DOUBLE_CLICK_INTERVAL,
                   cursor_position, get_monitor_locations, check_key_press)

try:
    import XInput
except ImportError:
    XInput = None


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

        # Warning message
        if XInput is None:
            print('Unable to load XInput library')

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

    def process_gui(self):
        """Process any commands being sent from the GUI."""
        if self.gui is None:
            return

        while self.gui.queue:
            command = self.gui.queue.pop(0)

            # Commands that must be executed
            if command in self.mapping_important:
                self.mapping_important[command]()

            # Commands that may only run if not paused
            elif command in self.mapping_pausable:
                if self.state != ThreadState.Paused:
                    self.mapping_pausable[command]()

    def run(self):
        """Main loop to do all the realtime processing."""
        check_monitors_interval = 1
        check_monitors_override = False
        check_gamepad_interval = 60
        check_gamepad_override = False

        old_mouse_pos = old_monitors = None
        old_monitor_index = monitor_index = None
        keys = {item: [0] * 255 for item in ('tick', 'prev', 'count', 'held')}
        gamepads = {item: [(0, 0)] * 4 for item in ('thumb_l', 'thumb_r')}
        gamepads.update({item: [0] * 4 for item in ('trig_l', 'trig_r')})
        gamepads['buttons'] = {item: [defaultdict(int)] * 4 for item in ('tick', 'prev', 'count', 'held')}
        ticks = 0
        start = time.time()
        while self.state != ThreadState.Stopped:
            self.process_gui()

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
                    # Skip this loop and try again, but this time refresh the data
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

                # Get gamepad information
                if XInput is not None:
                    # Determine which gamepads are connected
                    if not ticks % check_gamepad_interval or check_gamepad_override:
                        check_gamepad_override = False
                        connected_gamepads = XInput.get_connected()

                    for gamepad in (i for i, active in enumerate(connected_gamepads) if active):
                        # Get a snapshot of the current gamepad state
                        try:
                            state = XInput.get_state(gamepad)
                        except XInput.XInputNotConnectedError:
                            continue
                        thumb_l, thumb_r = XInput.get_thumb_values(state)
                        trig_l, trig_r = XInput.get_trigger_values(state)
                        buttons = XInput.get_button_values(state)

                        if thumb_l != gamepads['thumb_l'][gamepad]:
                            print(f'Gamepad {gamepad+1} left thumb moved: {thumb_l}')
                        if thumb_r != gamepads['thumb_r'][gamepad]:
                            print(f'Gamepad {gamepad+1} right thumb moved: {thumb_r}')
                        if trig_l != gamepads['trig_l'][gamepad]:
                            print(f'Gamepad {gamepad+1} left trigger moved: {trig_l}')
                        if trig_r != gamepads['trig_r'][gamepad]:
                            print(f'Gamepad {gamepad+1} right trigger moved: {trig_r}')

                        gamepads['thumb_l'][gamepad] = thumb_l
                        gamepads['thumb_r'][gamepad] = thumb_r
                        gamepads['trig_l'][gamepad] = trig_l
                        gamepads['trig_r'][gamepad] = trig_r

                        for button, val in buttons.items():
                            previously_pressed = bool(gamepads['buttons']['tick'][gamepad][button])
                            currently_pressed = val

                            # Detect individual button releases
                            if previously_pressed and not currently_pressed:
                                print(f'Button released: {button}')
                                gamepads['buttons']['tick'][gamepad][button] = gamepads['buttons']['held'][gamepad][button] = 0

                            # Detect when a button is being held down
                            elif previously_pressed and currently_pressed:
                                gamepads['buttons']['held'][gamepad][button] += 1
                                print(f'Button held: {button}')

                            # Detect when a new button is pressed
                            elif not previously_pressed and currently_pressed:
                                print(f'Button pressed: {button}')

                                # Figure out if a double press happened
                                if ticks - gamepads['buttons']['prev'][gamepad][button] < self.double_click_ticks:
                                    gamepads['buttons']['count'][gamepad][button] += 1
                                    print(f'Presses detected: {gamepads["buttons"]["count"][gamepad][button]}')
                                else:
                                    gamepads['buttons']['count'][gamepad][button] = 1
                                gamepads['buttons']['tick'][gamepad][button] = gamepads['buttons']['prev'][gamepad][button] = ticks

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
