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
        self._q_main = multiprocessing.Queue()
        self._q_tracking = multiprocessing.Queue()
        self._q_processing = multiprocessing.Queue()
        self._q_gui = multiprocessing.Queue()

        self._p_tracking = multiprocessing.Process(target=tracking.run, args=(self._q_main, self._q_tracking))
        self._p_tracking.daemon = True
        self._p_processing = multiprocessing.Process(target=processing.run, args=(self._q_main, self._q_processing))
        self._p_processing.daemon = True
        self._p_gui = multiprocessing.Process(target=gui.run, args=(self._q_main, self._q_gui))
        self._p_gui.daemon = True

    def start_tracking(self):
        """Start the tracking."""
        self._start_tracking()
        self._q_main.put(ipc.TrackingState(ipc.TrackingState.State.Start))

    def _start_tracking(self):
        """Start the tracking processes if required."""
        print('Starting tracking processes...')
        tracking_running = self._p_tracking.is_alive()
        processing_running = self._p_processing.is_alive()
        if tracking_running and processing_running:
            print('Skipping: already running')
            return

        # Shut down any existing threads
        if tracking_running or processing_running:
            self.stop_tracking()

        # Empty queues
        while not self._q_tracking.empty():
            self._q_tracking.get()
        while not self._q_processing.empty():
            self._q_processing.get()

        self._q_main.put(ipc.TrackingState(ipc.TrackingState.State.Start))

        # Start processes
        self._p_tracking = multiprocessing.Process(target=tracking.run, args=(self._q_main, self._q_tracking))
        self._p_tracking.daemon = True
        self._p_tracking.start()
        self._p_processing = multiprocessing.Process(target=processing.run, args=(self._q_main, self._q_processing))
        self._p_processing.daemon = True
        self._p_processing.start()
        print('Started tracking processes')

    def stop_tracking(self):
        print('Sending stop tracking signal...')
        self._q_main.put(ipc.TrackingState(ipc.TrackingState.State.Stop))

        # print('Waiting for tracking to shut down...')
        # if self._p_tracking.is_alive():
        #     self._p_tracking.join()

        # print('Waiting for processing to shut down...')
        # if self._p_processing.is_alive():
        #     self._p_processing.join()

        print('Safely shut down processes')

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
                raise RuntimeError('test exception')

        return True

    def _start_queue_handler(self):
        running = True
        while True:
            # Get the next message
            # If the app is shutting down, then it will safely stop
            # after processing remaining messages
            try:
                received_message = self._q_main.get(timeout=None if running else 0.1)
            except queue.Empty:
                return

            if received_message.target & ipc.Target.Hub:
                if not self.process_data(received_message):
                    print('Exit requested, shutting down...')
                    running = False

            if received_message.target & ipc.Target.Tracking:
                self._q_tracking.put(received_message)

            if received_message.target & ipc.Target.Processing:
                self._q_processing.put(received_message)

            if received_message.target & ipc.Target.GUI:
                self._q_gui.put(received_message)

    def start_queue_handler(self):
        print('Queue handler started.')
        try:
            self._start_queue_handler()
        except Exception:
            self._q_main.put(ipc.Exit())
            raise
        print('Queue handler shut down.')

    def start_gui(self):
        self._p_gui.start()
