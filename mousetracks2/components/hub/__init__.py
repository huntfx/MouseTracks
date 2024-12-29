"""Setup individual components to the Mouse Tracks application.

Components:
    - tracking
    - processing
    - gui
    - cli
"""

import multiprocessing

from .. import ipc, tracking, processing, gui


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
        print('[Hub] Sending stop tracking signal...')
        self._process_message(ipc.TrackingState(ipc.TrackingState.State.Stop))

        # Wait for processes to end
        self._p_tracking.join()
        self._p_processing.join()

        # Empty queues
        while not self._q_tracking.empty():
            self._q_tracking.get()
        while not self._q_processing.empty():
            self._q_processing.get()

        print('[Hub] Tracking processes safely shut down')

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

    def _startup_tracking_processes(self):
        """Ensure the tracking processes exist.
        This will check that previous ones are shut down before starting
        up new ones.
        """
        print('[Hub] Checking tracking processes...')
        tracking_running = self._p_tracking.is_alive()
        processing_running = self._p_processing.is_alive()
        print(f'[Hub] Tracking process alive: {tracking_running}')
        print(f'[Hub] Processing process alive: {processing_running}')
        if tracking_running and processing_running:
            return

        # Shut down any existing processes if only one is running
        if tracking_running or processing_running:
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

    def run(self, gui: bool = True) -> None:
        """Setup the tracking."""
        if gui:
            self._p_gui.start()
        else:
            self.start_tracking()

        print('[Hub] Queue handler started.')
        running = True
        try:
            while running or not self._q_main.empty():
                try:
                    self._process_message(self._q_main.get())
                except ExitRequest:
                    print('[Hub] Exit requested, triggring shut down...')
                    running = False

        # Ensure threads are safely shut down
        finally:
            self.stop_tracking()

        print('[Hub] Queue handler shut down.')
