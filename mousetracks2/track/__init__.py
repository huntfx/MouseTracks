from functools import partial
from queue import Empty

from constants import *


class MainThread(object):
    """Main tracking script.
    This runs in realtime and sends data to a background thread for
    processing, and also handles the communication with the GUI.
    """

    def __init__(self, gui):
        """Setup the tracking thread.

        Parameters:
            gui (QObject): The main GUI.
                Requires a queue() and receiveFromThread(event) method.
                This was done instead of arguments since Qt doesn't
                cope well with sending signals across threads.
        """
        self.gui = gui
        self.start()

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

    def send_event(self, event):
        """Send an event back to the GUI.
        
        Parameters:
            event (ThreadEvent): Event to send to the GUI.
        """
        if not isinstance(event, ThreadEvent):
            event = ThreadEvent[event]
        self.gui.receiveFromThread(event)
    
    def start(self):
        """Mark the script as started."""
        self._running = True
        self.pause(False)
        self.send_event(ThreadEvent.Started)
    
    def running(self):
        """Get if the script is still running."""
        return self._running

    def stop(self):
        """Mark the script as stopped."""
        self._running = False
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
                pause = not self._pause
            except AttributeError:
                pause = True
        self._pause = pause

        if pause:
            self.send_event(ThreadEvent.Paused)
        else:
            self.send_event(ThreadEvent.Unpaused)

    def paused(self):
        """Return True or False if the thread is in a paused state."""
        return self._pause

    def get_commands(self):
        """Generator to get information from the main thread.
        The data is sorted by order of importance.
        """
        commands = []
        while not self.gui.queue().empty():
            try:
                yield self.gui.queue().get(False)
            except Empty:
                continue

    def main(self):
        """Main loop to do all the realtime processing."""
        paused = False
        while self.running():
            # Handle any GUI commands
            for data in self.get_commands():
                # Important commands
                if data in self.mapping_important:
                    self.mapping_important[data]()

                # Pausable commands
                elif data in self.mapping_pausable:
                    if not self.paused():
                        self.mapping_pausable[data]()

    def run(self):
        """Execute the main loop and catch any errors."""
        try:
            self.main()
        except BaseException:
            self.send_event(ThreadEvent.Exception)
            raise


def run(gui):
    """Wrap the class in a function that can be run."""
    MainThread(gui).run()
