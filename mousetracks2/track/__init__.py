import time
from collections import defaultdict
from functools import partial
from queue import Empty
from multiprocessing import Queue

from constants import *
from track import process
from utils import DOUBLE_CLICK_INTERVAL, cursor_position, get_monitor_locations, check_key_press

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

        # Start background process
        self.process_sender = Queue()
        self.process_receiver = Queue()
        self.process = process.start(self.process_sender, self.process_receiver)

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

    def send_gui_event(self, event, *args, **kwargs):
        """Send an event back to the GUI.

        Parameters:
            event (ThreadEvent): Event to send.
        """
        if self.gui is None:
            return
        if not isinstance(event, ThreadEvent):
            event = ThreadEvent[event]
        self.gui.receiveFromThread(event, *args, **kwargs)

    def send_process_event(self, event, *args):
        """Send an event to the processing thread.
        This should also print out what's happening.

        Parameters:
            event (ProcessEvent): Event to send.
        """
        event_messages = {
            ProcessEvent.MouseMove: 'Mouse moved: {}',
            ProcessEvent.KeyPressed: 'Key pressed: {} (x{})',
            ProcessEvent.KeyHeld: 'Key held: {}',
            ProcessEvent.KeyReleased: 'Key released: {}',
            ProcessEvent.GamepadButtonPressed: 'Gamepad {} button pressed: {} (x{})',
            ProcessEvent.GamepadButtonHeld: 'Gamepad {} button held: {}',
            ProcessEvent.GamepadButtonReleased: 'Gamepad {} button released: {}',
            ProcessEvent.GamepadThumbL: 'Gamepad {} left thumbstick moved: {}',
            ProcessEvent.GamepadThumbR: 'Gamepad {} right thumbstick moved: {}',
            ProcessEvent.GamepadTriggerL: 'Gamepad {} left trigger moved: {}',
            ProcessEvent.GamepadTriggerR: 'Gamepad {} right trigger moved: {}',
        }
        if event in event_messages:
            print(event_messages[event].format(*args))
        elif event == ProcessEvent.MonitorChanged:
            monitor_data = args[0]
            resolutions = ('{}x{}'.format(x2-x1, y2-y1) for x1, y1, x2, y2 in monitor_data)
            coordinates = ((x1, y1) for x1, y1, x2, y2 in monitor_data)
            monitor_str = ', '.join('{} at {}'.format(*i) for i in zip(resolutions, coordinates))
            print('Monitor setup changed: ' + monitor_str)

        self.process_sender.put((event, args))

    def start(self):
        """Mark the script as started."""
        self.pause(False)
        self.state = ThreadState.Running
        self.send_gui_event(ThreadEvent.Started)

    def stop(self):
        """Mark the script as stopped."""
        self.state = ThreadState.Stopped
        self.send_gui_event(ThreadEvent.Stopped)

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
            self.send_gui_event(ThreadEvent.Paused)
        else:
            self.state = ThreadState.Running
            self.send_gui_event(ThreadEvent.Unpaused)

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
        check_monitors_interval = 60
        check_monitors_override = False
        check_gamepad_interval = 60
        check_gamepad_override = False

        old_mouse_pos = old_monitors = None
        old_monitor_index = monitor_index = None
        connected_gamepads = old_gamepads = [False] * 4
        keys = {item: [0] * 255 for item in ('tick', 'prev', 'count', 'held')}
        gamepads = {item: [(0, 0)] * 4 for item in ('thumb_l', 'thumb_r')}
        gamepads.update({item: [0] * 4 for item in ('trig_l', 'trig_r')})
        gamepads['buttons'] = {item: [defaultdict(int)] * 4 for item in ('tick', 'prev', 'count', 'held')}
        ticks = 0
        start = time.time()
        while self.state != ThreadState.Stopped:
            self.process_gui()

            # Receive data from the processing thread
            while not self.process_receiver.empty():
                received = self.process_receiver.get()
                if isinstance(received, Exception):
                    return self.stop()

            # Get monitor data
            if not ticks % check_monitors_interval or check_monitors_override:
                check_monitors_override = False
                monitors = get_monitor_locations()
            monitors_changed = monitors != old_monitors
            if monitors_changed:
                self.send_process_event(ProcessEvent.MonitorChanged, monitors)

            # Handle realtime data
            if self.state == ThreadState.Running:
                # Get mouse data
                mouse_pos = cursor_position()
                mouse_moved = mouse_pos != old_mouse_pos

                # Get keyboard/mouse clicks
                # Note this will not see anything faster than 1/60th of a second
                for key, val in enumerate(keys['tick']):
                    previously_pressed = bool(val)
                    currently_pressed = bool(check_key_press(key))

                    # Detect individual key releases
                    if previously_pressed and not currently_pressed:
                        keys['tick'][key] = keys['held'][key] = 0
                        self.send_process_event(ProcessEvent.KeyReleased, key)

                    # Detect when a key is being held down
                    elif previously_pressed and currently_pressed:
                        keys['held'][key] += 1
                        self.send_process_event(ProcessEvent.KeyHeld, key)

                    # Detect when a new key is pressed
                    elif not previously_pressed and currently_pressed:
                        if ticks - keys['prev'][key] < self.double_click_ticks:
                            keys['count'][key] += 1
                        else:
                            keys['count'][key] = 1
                        keys['tick'][key] = keys['prev'][key] = ticks
                        self.send_process_event(ProcessEvent.KeyPressed, key, keys['count'][key])

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
                            self.send_gui_event(ThreadEvent.MouseMove, remapped)
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
                    self.send_process_event(ProcessEvent.MouseMove, mouse_pos)

                # Get gamepad information
                if XInput is not None:
                    # Determine which gamepads are connected
                    if not ticks % check_gamepad_interval or check_gamepad_override:
                        check_gamepad_override = False
                        connected_gamepads = XInput.get_connected()
                    gamepads_changed = connected_gamepads != old_gamepads

                    # Print message saying when a change is detected
                    if gamepads_changed:
                        diff = sum(filter(bool, connected_gamepads))
                        if old_gamepads is not None:
                            diff -= sum(filter(bool, old_gamepads))
                        print('Gamepad ' + ('removed', 'detected')[diff > 0])

                    for gamepad in (i for i, active in enumerate(connected_gamepads) if active):
                        # Get a snapshot of the current gamepad state
                        try:
                            state = XInput.get_state(gamepad)
                        except XInput.XInputNotConnectedError:
                            check_gamepad_override = True
                            continue
                        thumb_l, thumb_r = XInput.get_thumb_values(state)
                        trig_l, trig_r = XInput.get_trigger_values(state)
                        buttons = XInput.get_button_values(state)

                        if thumb_l != gamepads['thumb_l'][gamepad]:
                            self.send_processEvent(ProcessEvent.GamepadThumbL, gamepad, thumb_l)
                        if thumb_r != gamepads['thumb_r'][gamepad]:
                            self.send_processEvent(ProcessEvent.GamepadThumbR, gamepad, thumb_r)
                        if trig_l != gamepads['trig_l'][gamepad]:
                            self.send_processEvent(ProcessEvent.GamepadTriggerL, gamepad, trig_l)
                        if trig_r != gamepads['trig_r'][gamepad]:
                            self.send_processEvent(ProcessEvent.GamepadTriggerR, gamepad, trig_r)

                        gamepads['thumb_l'][gamepad] = thumb_l
                        gamepads['thumb_r'][gamepad] = thumb_r
                        gamepads['trig_l'][gamepad] = trig_l
                        gamepads['trig_r'][gamepad] = trig_r

                        for button, val in buttons.items():
                            previously_pressed = bool(gamepads['buttons']['tick'][gamepad][button])
                            currently_pressed = val

                            # Detect individual button releases
                            if previously_pressed and not currently_pressed:
                                gamepads['buttons']['tick'][gamepad][button] = gamepads['buttons']['held'][gamepad][button] = 0
                                self.send_process_event(ProcessEvent.GamepadButtonReleased, gamepad, button)

                            # Detect when a button is being held down
                            elif previously_pressed and currently_pressed:
                                gamepads['buttons']['held'][gamepad][button] += 1
                                self.send_process_event(ProcessEvent.GamepadButtonHeld, gamepad, button)

                            # Detect when a new button is pressed
                            elif not previously_pressed and currently_pressed:
                                count = gamepads['buttons']['count'][gamepad]
                                prev = gamepads['buttons']['prev'][gamepad]
                                if ticks - prev[button] < self.double_click_ticks:
                                    count[button] += 1
                                else:
                                    count[button] = 1
                                gamepads['buttons']['tick'][gamepad][button] = prev[button] = ticks
                                self.send_process_event(ProcessEvent.GamepadButtonPressed, gamepad, button, count[button])

                # Store old values
                old_mouse_pos = mouse_pos
                old_monitors = monitors
                old_monitor_index = monitor_index
                old_gamepads = connected_gamepads

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
        main.send_gui_event(ThreadEvent.Exception)
        raise
