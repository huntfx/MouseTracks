"""Setup individual components to the Mouse Tracks application.

Components:
    - tracking
    - processing
    - gui
    - cli
"""

import time
import multiprocessing
import queue

from .. import ipc, app_detection, tracking, processing, gui
from ...constants import UPDATES_PER_SECOND


class ExitRequest(Exception):
    """Custom exception to raise and catch when an exit is requested."""


class Hub:
    """Set up individual components with queues for communication."""

    def __init__(self):
        """Initialise the hub with queues and processes."""
        # Setup queues
        self._q_main = multiprocessing.Queue()
        self._q_tracking = multiprocessing.Queue()
        self._q_processing = multiprocessing.Queue()
        self._q_gui = multiprocessing.Queue()
        self._q_app_detection = multiprocessing.Queue()

        # Setup processes
        self._p_gui = multiprocessing.Process(target=gui.run, args=(self._q_main, self._q_gui))
        self._p_gui.daemon = True
        self._create_tracking_processes()

    def start_tracking(self) -> None:
        """Start the tracking.
        This will load the threads and send a signal to them.
        """
        print('[Hub] Sending start tracking signal...')
        self._process_message(ipc.TrackingState(ipc.TrackingState.State.Start))

    def stop_tracking(self):
        """Stop the tracking processes.

        A stop signal is pushed to the queue, so that the processes can
        finish what they're doing then exit. Joining before the process
        has already exited will cause a lock, so waiting until they
        send a close notification back is required.
        If one thread is doing something particularly heavy, an attempt
        will be made to wait for it, but it will eventually terminate.
        """
        print('[Hub] Sending stop tracking signal...')
        self._process_message(ipc.TrackingState(ipc.TrackingState.State.Stop))

        print('[Hub] Waiting for close notification from processes...')
        tracking_running = self._p_tracking.is_alive()
        processing_running = self._p_processing.is_alive()
        app_detection_running = self._p_app_detection.is_alive()
        while tracking_running or processing_running or app_detection_running:
            try:
                match self._q_main.get(timeout=30):
                    case ipc.ProcessShutDownNotification(source=ipc.Target.Tracking):
                        tracking_running = False
                    case ipc.ProcessShutDownNotification(source=ipc.Target.Processing):
                        processing_running = False
                    case ipc.ProcessShutDownNotification(source=ipc.Target.AppDetection):
                        app_detection_running = False
            except queue.Empty:
                if tracking_running:
                    print('[Hub] No notification received from tracking, terminating...')
                    self._p_tracking.terminate()
                if processing_running:
                    print('[Hub] No notification received from processing, terminating...')
                    self._p_processing.terminate()
                if app_detection_running:
                    print('[Hub] No notification received from application detection, terminating...')
                    self._p_app_detection.terminate()
                break

        # Wait for processes to end
        print('[Hub] Joining processes...')
        self._p_tracking.join()
        self._p_processing.join()
        self._p_app_detection.join()

        # Flush process queues
        # This is only in case of restarting the tracking again
        while not self._q_tracking.empty():
            self._q_tracking.get()
        while not self._q_processing.empty():
            self._q_processing.get()
        while not self._q_app_detection.empty():
            self._q_app_detection.get()

        print('[Hub] Processes shut down')

    def _create_tracking_processes(self) -> None:
        """Setup the processes required for tracking.
        If these are shut down, then a new process needs to be created.
        """
        print('[Hub] Creating tracking processes...')
        self._p_tracking = multiprocessing.Process(target=tracking.run, args=(self._q_main, self._q_tracking))
        self._p_tracking.daemon = True
        self._p_tracking.start()
        self._p_processing = multiprocessing.Process(target=processing.run, args=(self._q_main, self._q_processing))
        self._p_processing.daemon = True
        self._p_processing.start()
        self._p_app_detection = multiprocessing.Process(target=app_detection.run, args=(self._q_main, self._q_app_detection))
        self._p_app_detection.daemon = True
        self._p_app_detection.start()

    def _startup_tracking_processes(self):
        """Ensure the tracking processes exist.
        This will check that previous ones are shut down before starting
        up new ones.
        """
        print('[Hub] Checking tracking processes...')
        tracking_running = self._p_tracking.is_alive()
        processing_running = self._p_processing.is_alive()
        app_detection_running = self._p_app_detection.is_alive()
        print(f'[Hub] Tracking process alive: {tracking_running}')
        print(f'[Hub] Processing process alive: {processing_running}')
        print(f'[Hub] Application Detection process alive: {app_detection_running}')
        if tracking_running and processing_running and app_detection_running:
            return

        # Shut down any existing processes if only one is running
        if tracking_running or processing_running or app_detection_running:
            print('[Hub] Shutting down existing processes before starting new ones')
            self.stop_tracking()

        # Start processes
        self._create_tracking_processes()
        print('[Hub] Started tracking processes')

    def _process_message(self, message: ipc.Message) -> None:
        """Execute or forward a message based on its target."""
        # Process messages meant for the hub
        if message.target & ipc.Target.Hub:
            match message:
                case ipc.TrackingState(state=ipc.TrackingState.State.Start):
                    self._startup_tracking_processes()

                case ipc.Exit():
                    raise ExitRequest

                case ipc.Traceback():
                    message.reraise()

                case ipc.DebugRaiseError():
                    raise RuntimeError('[Hub] Test Exception')

        # Forward messages to the tracking process
        if message.target & ipc.Target.Tracking:
            self._q_tracking.put(message)

        # Forward messages to the processing process
        if message.target & ipc.Target.Processing:
            self._q_processing.put(message)

        # Forward messages to the GUI process
        if message.target & ipc.Target.GUI:
            self._q_gui.put(message)

        # Forward messages to the app detection process
        if message.target & ipc.Target.AppDetection:
            self._q_app_detection.put(message)

    def run(self, gui: bool = True) -> None:
        """Setup the tracking."""
        if gui:
            self._p_gui.start()
        else:
            self.start_tracking()

        running = True
        print('[Hub] Queue handler started.')
        try:
            while running or not self._q_main.empty():
                try:
                    self._process_message(self._q_main.get())
                except ExitRequest:
                    print('[Hub] Exit requested, triggering shut down...')
                    running = False

                    # Avoid shutting down before tracking can respond
                    # Without this, the save on exit feature won't work
                    time.sleep(1 / UPDATES_PER_SECOND)

        # Ensure threads are safely shut down
        finally:
            self.stop_tracking()

        print('[Hub] Queue handler shut down.')
