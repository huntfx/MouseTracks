"""Setup individual components to the Mouse Tracks application.

Components:
    - tracking
    - processing
    - gui
    - cli
"""

import multiprocessing

from .. import ipc, tracking, processing


class Hub:
    """Set up individual components with queues for communication."""

    def __init__(self):
        self._q_main = multiprocessing.Queue()
        self._q_tracking = multiprocessing.Queue()
        self._q_processing = multiprocessing.Queue()

        self._p_tracking = multiprocessing.Process(target=tracking.run, args=(self._q_main, self._q_tracking))
        self._p_processing = multiprocessing.Process(target=processing.run, args=(self._q_main, self._q_processing))

    def start_tracking(self):
        print('Starting up tracking threads...')
        tracking_alive = self._p_tracking.is_alive()
        processing_alive = self._p_processing.is_alive()

        # Empty queues
        if not tracking_alive:
            while not self._q_tracking.empty():
                self._q_tracking.get()
        if not processing_alive:
            while not self._q_processing.empty():
                self._q_processing.get()

        # Start processes
        if not tracking_alive:
            self._p_tracking.start()
        if not processing_alive:
            self._p_processing.start()

    def stop_tracking(self):
        tracking_alive = self._p_tracking.is_alive()
        processing_alive = self._p_processing.is_alive()
        if not tracking_alive and not processing_alive:
            return

        print('Sending stop tracking signals...')
        if tracking_alive:
            self._q_tracking.put(ipc.QueueItem(ipc.Target.Tracking, ipc.Type.Exit))
        if processing_alive:
            self._q_processing.put(ipc.QueueItem(ipc.Target.Processing, ipc.Type.Exit))

    def stop(self):
        self._q_main.put(ipc.QueueItem(ipc.Target.Hub, ipc.Type.Exit))

    def _start_queue_handler(self):
        while True:
            received_message = self._q_main.get()

            match received_message.target:
                # Handle own messages
                case ipc.Target.Hub:
                    match received_message.type:

                        # An error has been raised
                        case ipc.Type.Traceback:
                            exc, tb = received_message.data
                            # Replicate Python's default behaviour
                            print(tb)
                            print('During handling of the above exception, another exception occurred:\n')
                            raise exc

                        # Exit the process
                        # Note that any subprocesses must be shut down first
                        case ipc.Type.Exit:
                            self.stop_tracking()
                            return

                # Forward messages to the tracking process
                case ipc.Target.Tracking:
                    self._q_tracking.put(received_message)

                # Forward messages to the processing process
                case ipc.Target.Processing:
                    self._q_processing.put(received_message)

                case _:
                    print(f'Unknown message: {received_message}')

    def start_queue_handler(self):
        try:
            self._start_queue_handler()
        except Exception:
            self.stop()
            raise


if __name__ == '__main__':
    hub = Hub()
    hub.start_tracking()
    hub.start_queue_handler()
