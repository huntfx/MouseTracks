from multiprocessing import Process

from constants import ProcessEvent


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

        self.event_mapping = {
            ProcessEvent.MonitorChanged: self.monitor_change,
            ProcessEvent.MouseMove: self.mouse_mouse,
            ProcessEvent.KeyPressed: self.key_press,
            ProcessEvent.KeyHeld: self.key_held,
            ProcessEvent.KeyReleased: self.key_release,
            ProcessEvent.GamepadButtonPressed: self.gamepad_button_press,
            ProcessEvent.GamepadButtonHeld: self.gamepad_button_held,
            ProcessEvent.GamepadButtonReleased: self.gamepad_button_release,
            ProcessEvent.GamepadThumbL: self.gamepad_thumb_l,
            ProcessEvent.GamepadThumbR: self.gamepad_thumb_r,
            ProcessEvent.GamepadTriggerL: self.gamepad_trigger_l,
            ProcessEvent.GamepadTriggerR: self.gamepad_trigger_r,
        }

    def run(self):
        """Handle all heavy processing."""
        try:
            while True:
                event, data = self.receiver.get()
                self.event_mapping[event](*data)

        # Signal to the main thread that an error occurred
        except Exception as e:
            self.sender.put(e)
            raise

    def monitor_change(self, data): pass

    def mouse_mouse(self, pos): pass

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
