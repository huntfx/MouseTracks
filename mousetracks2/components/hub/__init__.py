"""Setup individual components to the Mouse Tracks application.

Components:
    - tracking
    - processing
    - gui
    - cli
"""

import multiprocessing
import queue

from .. import ipc, tracking, processing, gui


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

    def _create_tracking_processes(self) -> None:
        """Setup the processes required for tracking.
        If these are shut down, then a new process needs to be created.
        """
        self._p_tracking = multiprocessing.Process(target=tracking.run, args=(self._q_main, self._q_tracking))
        self._p_tracking.daemon = True
        self._p_tracking.start()
        self._p_processing = multiprocessing.Process(target=processing.run, args=(self._q_main, self._q_processing))
        self._p_processing.daemon = True
        self._p_processing.start()

    def start_tracking(self) -> None:
        """Start the tracking.
        This will load the threads and send a signal to them.
        """
        print('[Hub] Sending start tracking signal...')
        self._q_main.put(ipc.TrackingState(ipc.TrackingState.State.Start))

    def stop_tracking(self):
        print('[Hub] Sending stop tracking signal...')
        self._q_main.put(ipc.TrackingState(ipc.TrackingState.State.Stop))

    def _start_tracking(self):
        """Start up the tracking processes if required."""
        print('[Hub] Starting tracking processes...')
        tracking_running = self._p_tracking.is_alive()
        processing_running = self._p_processing.is_alive()
        if tracking_running and processing_running:
            print('[Hub] Tracking already running')
            return

        # Shut down any existing threads
        if tracking_running or processing_running:
            self.stop_tracking()

        # Empty queues
        while not self._q_tracking.empty():
            self._q_tracking.get()
        while not self._q_processing.empty():
            self._q_processing.get()

        # Start processes
        self._create_tracking_processes()
        print('[Hub] Started tracking processes')

    def cleanup_on_exit(self):
        """Safely close down processes on exit."""
        self._p_tracking.join()
        self._p_processing.join()
        print('[Hub] Safely shut down processes')

    def process_data(self, message: ipc.Message):
        match message:
            case ipc.TrackingState(state=ipc.TrackingState.State.Start):
                self._start_tracking()

            case ipc.Exit():
                self.stop_tracking()
                return False

            case ipc.Traceback():
                message.reraise()

            case ipc.DebugRaiseError():
                raise RuntimeError('[Hub] Test Exception')

        return True

    def _start_queue_handler(self, running=True):
        while True:
            # Get the next message
            try:
                received_message = self._q_main.get(timeout=None if running else 0.1)

            # Process all remaining messages before shutdown
            except queue.Empty:
                break

            if received_message.target & ipc.Target.Hub:
                if not self.process_data(received_message):
                    print('[Hub] Exit requested, shutting down...')
                    running = False

            if received_message.target & ipc.Target.Tracking:
                self._q_tracking.put(received_message)

            if received_message.target & ipc.Target.Processing:
                self._q_processing.put(received_message)

            if received_message.target & ipc.Target.GUI:
                self._q_gui.put(received_message)

        self.cleanup_on_exit()

    def start_queue_handler(self):
        print('[Hub] Queue handler started.')
        try:
            self._start_queue_handler()

        # If an error occurs, trigger a safe shutdown
        except Exception:
            self._q_main.put(ipc.Exit())
            self._start_queue_handler(running=False)
            raise

        print('[Hub] Queue handler shut down.')

    def start_gui(self):
        self._p_gui.start()
