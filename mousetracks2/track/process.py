from multiprocessing import Process

from constants import ProcessCommand, ProcessEvent
from utils import match_pixel_to_monitor
from utils.math import calculate_line, calculate_distance


def start(sender, receiver):
    """Start the background process."""
    background_process = BackgroundProcess(sender, receiver)
    process = Process(target=background_process.run)
    process.daemon = True
    process.start()
    return process


class BackgroundProcess(object):
    def __init__(self, receiver, sender):
        self.receiver = receiver
        self.sender = sender

        self.command_mapping = {
            ProcessCommand.Pause: self.pause,
            ProcessCommand.Tick: self.tick,
            ProcessCommand.MonitorChanged: self.monitor_change,
            ProcessCommand.MouseMove: self.mouse_mouse,
            ProcessCommand.KeyPressed: self.key_press,
            ProcessCommand.KeyHeld: self.key_held,
            ProcessCommand.KeyReleased: self.key_release,
            ProcessCommand.GamepadButtonPressed: self.gamepad_button_press,
            ProcessCommand.GamepadButtonHeld: self.gamepad_button_held,
            ProcessCommand.GamepadButtonReleased: self.gamepad_button_release,
            ProcessCommand.GamepadThumbL: self.gamepad_thumb_l,
            ProcessCommand.GamepadThumbR: self.gamepad_thumb_r,
            ProcessCommand.GamepadTriggerL: self.gamepad_trigger_l,
            ProcessCommand.GamepadTriggerR: self.gamepad_trigger_r,
        }

        self.ticks = 0

    def send_event(self, event, *data):
        self.sender.put((event, data))

    def run(self):
        """Wait for commands and process them."""
        try:
            while True:
                command, data = self.receiver.get()
                self.command_mapping[command](*data)

        # Signal to the main thread that an error occurred
        except Exception as e:
            self.send_event(ProcessEvent.Error)
            raise

    def tick(self, ticks):
        """Keep a count of all the ticks.
        For now, ignore the "total" tick value as it's not needed.
        """
        self.ticks += 1

    def pause(self):
        """Reset certain settings on pause."""
        self.mouse_pos = None

    def monitor_change(self, data):
        """Record new monitor data."""
        self.monitor_data = data

    def mouse_mouse(self, pos):
        """Record mouse movement."""
        try:
            prev_mouse_pos = self.mouse_pos
        except AttributeError:
            prev_mouse_pos = None

        self.mouse_pos = pos

        # In certain cases such as the login screen, the position can't be read
        if self.mouse_pos is None:
            if prev_mouse_pos is not None:
                print('Unknown mouse position')
            return

        # Calculate the distance (or speed)
        distance = calculate_distance(self.mouse_pos, prev_mouse_pos)
        if distance:
            self.send_event(ProcessEvent.MouseDistance, distance)

        # Draw a line from the previous position
        pixels = [self.mouse_pos]
        if prev_mouse_pos is not None:
            pixels.extend(calculate_line(self.mouse_pos, prev_mouse_pos))
            pixels.append(prev_mouse_pos)

        # Determine which monitor each pixel is on
        start_monitor = match_pixel_to_monitor(pixels[0], self.monitor_data)
        if len(pixels) == 1:
            end_monitor = start_monitor
        else:
            end_monitor = match_pixel_to_monitor(pixels[-1], self.monitor_data)

        if start_monitor == end_monitor:
            monitor_mapping = {pixel: start_monitor for pixel in pixels}
        else:
            monitor_mapping = {
                pixels[0]: start_monitor,
                pixels[-1]: end_monitor,
            }
            for pixel in pixels[1:-1]:
                monitor_mapping[pixel] = match_pixel_to_monitor(pixel, self.monitor_data)

        for pixel, i in monitor_mapping.items():
            x1, y1, x2, y2 = self.monitor_data[i]
            width = x2 - x1
            height = y2 - y1
            #mtfile.record_mouse_movement(pixel=pixel, resolution=(width, height), ticks=self.ticks, speed=distance)

    def key_press(self, key, count): pass

    def key_held(self, key): pass

    def key_release(self, key): pass

    def gamepad_button_press(self, gamepad, button, count): pass

    def gamepad_button_held(self, gamepad, button): pass

    def gamepad_button_release(self, gamepad, button): pass

    def gamepad_thumb_l(self, gamepad, pos): pass

    def gamepad_thumb_r(self, gamepad, pos): pass

    def gamepad_trigger_l(self, gamepad, value): pass

    def gamepad_trigger_r(self, gamepad, value): pass
