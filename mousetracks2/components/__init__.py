"""Setup individual components to the Mouse Tracks application.

Components:
    - tracking
    - processing
    - gui
    - cli
"""

from __future__ import annotations

import os
import sys
import time
import traceback
import multiprocessing
import multiprocessing.queues
import queue
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Generic, TypeVar

from . import app_detection, gui, ipc, processing, tracking
from ..config import GlobalConfig, should_minimise_on_start
from ..constants import IS_EXE, UPDATES_PER_SECOND
from ..exceptions import ExitRequest

if TYPE_CHECKING:
    from multiprocessing.sharedctypes import Synchronized
    from ..utils.system.win32 import WindowHandle


T = TypeVar('T')


class Queue(multiprocessing.queues.Queue, Generic[T]):
    """Custom implementation of a queue to ensure `qsize()` works.

    If it is not available, then `multiprocessing.Value` will be used
    instead as the counter.
    """

    @dataclass
    class State:
        """Store the class state for serialisation."""

        original: Any
        counter: Synchronized[int]
        use_counter: bool

    def __init__(self) -> None:
        self._use_custom_counter = False
        super().__init__(ctx=multiprocessing.get_context())
        try:
            super().qsize()
        except NotImplementedError:
            self._use_custom_counter = True
        self._counter: Synchronized[int] = multiprocessing.Value('i', 0)

    def __getstate__(self) -> State:
        return self.State(super().__getstate__(), self._counter, self._use_custom_counter)

    def __setstate__(self, state: State) -> None:
        self._counter = state.counter
        self._use_custom_counter = state.use_counter
        super().__setstate__(state.original)  # type: ignore

    def qsize(self) -> int:
        """Get the queue size."""
        if self._use_custom_counter:
            return self._counter.value
        return super().qsize()

    def put(self, obj: T, block: bool = True, timeout: float | None = None) -> Any:
        """Add an item to the queue."""
        super().put(obj, block, timeout)
        if self._use_custom_counter:
            with self._counter.get_lock():
                self._counter.value += 1

    def get(self, block: bool = True, timeout: float | None = None) -> T:
        """Get an item from the queue."""
        if self._use_custom_counter:
            with self._counter.get_lock():
                self._counter.value -= 1
        return super().get(block, timeout)


class Hub:
    """Set up individual components with queues for communication."""

    def __init__(self, use_gui: bool = True) -> None:
        """Initialise the hub with queues and processes."""
        self.state = ipc.TrackingState.Paused
        self.use_gui = use_gui
        self._previous_component_check: float = 0.0

        self._wait_to_load = {ipc.Target.AppDetection, ipc.Target.Tracking, ipc.Target.Processing}
        if self.use_gui:
            self._wait_to_load.add(ipc.Target.GUI)

        self._q_main: Queue[ipc.Message] = Queue()

        self._q_gui: Queue[ipc.Message] = Queue()
        self._p_gui = multiprocessing.Process(target=gui.GUI.launch, args=(self._q_main, self._q_gui))
        self._p_gui.daemon = True
        if self.use_gui:
            self._p_gui.start()
        self._create_tracking_processes()

        # Disable show/hide if console is already hidden
        handle = self._get_console_handle()
        if handle is None or not handle.visible or not handle.pid or not handle.title:
            self._q_main.put(ipc.InvalidConsole())

    def start_tracking(self) -> None:
        """Start the tracking.
        This will load the threads and send a signal to them.
        """
        print('[Hub] Sending start tracking signal...')
        self._process_message(ipc.StartTracking())

    def stop_tracking(self) -> None:
        """Stop the tracking processes.

        A stop signal is pushed to the queue, so that the processes can
        finish what they're doing then exit. Joining before the process
        has already exited will cause a lock, so waiting until they
        send a close notification back is required.
        If one thread is doing something particularly heavy, an attempt
        will be made to wait for it, but it will eventually terminate.

        In the case of an unclean shutdown, it can leave the queues in a
        corrupt state, where they cannot be emptied, and therefore the
        application can't exit. Using `cancel_join_thread` will discard
        all data and allow the application to close.
        """
        print('[Hub] Sending stop tracking signal...')
        self._process_message(ipc.StopTracking())

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

        # Ensure queues are closed
        print('[Hub] Closing queues...')
        self._q_tracking.close()
        self._q_processing.close()
        self._q_app_detection.close()

        # Discard any data left in the queue
        print('[Hub] Flushing queues...')
        self._q_tracking.cancel_join_thread()
        self._q_processing.cancel_join_thread()
        self._q_app_detection.cancel_join_thread()

        print('[Hub] Processes shut down')

    def _create_tracking_processes(self) -> None:
        """Setup the processes required for tracking.
        If these are shut down, then a new process needs to be created.
        """
        print('[Hub] Creating tracking processes...')
        self._q_tracking: Queue[ipc.Message] = Queue()
        self._p_tracking = multiprocessing.Process(target=tracking.Tracking.launch, args=(self._q_main, self._q_tracking))
        self._p_tracking.daemon = True
        self._p_tracking.start()

        self._q_processing: Queue[ipc.Message] = Queue()
        self._p_processing = multiprocessing.Process(target=processing.Processing.launch, args=(self._q_main, self._q_processing))
        self._p_processing.daemon = True
        self._p_processing.start()

        self._q_app_detection: Queue[ipc.Message] = Queue()
        self._p_app_detection = multiprocessing.Process(target=app_detection.AppDetection.launch, args=(self._q_main, self._q_app_detection))
        self._p_app_detection.daemon = True
        self._p_app_detection.start()

    def _startup_tracking_processes(self) -> None:
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
                case ipc.StartTracking():
                    self.state = ipc.TrackingState.Running
                    self._startup_tracking_processes()

                case ipc.PauseTracking():
                    self.state = ipc.TrackingState.Paused

                case ipc.StopTracking():
                    self.state = ipc.TrackingState.Stopped

                case ipc.Exit():
                    raise ExitRequest

                case ipc.Traceback():
                    message.reraise()

                case ipc.DebugRaiseError():
                    raise RuntimeError('[Hub] Test Exception')

                case ipc.RequestQueueSize():
                    self._q_main.put(ipc.QueueSize(self._q_main.qsize(),
                                                   self._q_tracking.qsize(),
                                                   self._q_processing.qsize(),
                                                   self._q_gui.qsize(),
                                                   self._q_app_detection.qsize()))

                case ipc.ToggleConsole():
                    self._toggle_console(message.show)

                case ipc.RequestPID():
                    self._q_main.put(ipc.SendPID(source=ipc.Target.Hub, pid=os.getpid()))

                case ipc.ComponentLoaded():
                    self._wait_to_load.discard(message.component)
                    if not self._wait_to_load:
                        self._q_main.put(ipc.AllComponentsLoaded())

                case ipc.AllComponentsLoaded():
                    self.start_tracking()

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

    def _get_console_handle(self) -> WindowHandle | None:
        """Get the handle to the console."""
        if sys.platform == 'win32':
            from ..utils.system.win32 import WindowHandle, get_window_handle
            return WindowHandle(get_window_handle(console=True))
        return None

    def _toggle_console(self, show: bool) -> None:
        """Show or hide the console."""
        handle = self._get_console_handle()
        if handle is None or not handle.pid or not handle.title:
            self._q_main.put(ipc.InvalidConsole())
        elif show:
            handle.show()
        else:
            handle.hide()

    def _test_components(self) -> None:
        """Check that all components are running.
        If this fails an error will be raised.
        """
        current_time = time.time()
        if self._previous_component_check + GlobalConfig.component_check_frequency > current_time:
            return

        if self.state == ipc.TrackingState.Running:
            if not self._p_tracking.is_alive():
                raise RuntimeError('[Hub] Unexpected shutdown of Tracking component')
            if not self._p_processing.is_alive():
                raise RuntimeError('[Hub] Unexpected shutdown of Processing component')
            if not self._p_app_detection.is_alive():
                raise RuntimeError('[Hub] Unexpected shutdown of Application Detection component')
            if self.use_gui and not self._p_gui.is_alive():
                raise RuntimeError('[Hub] Unexpected shutdown of GUI component')
        self._previous_component_check = current_time

    def run(self) -> None:
        """Setup the tracking."""
        print('[Hub] Launching application...')
        running = True
        error_occurred = False

        try:
            if self.use_gui and (IS_EXE or should_minimise_on_start()):
                self._process_message(ipc.ToggleConsole(False))

            # Listen for events
            print('[Hub] Queue handler started.')
            while running or not self._q_main.empty():
                self._test_components()
                try:
                    self._process_message(self._q_main.get())

                except ExitRequest:
                    print('[Hub] Exit requested, triggering shut down...')
                    running = False

                    # Avoid shutting down before tracking can respond
                    # Without this, the save on exit feature won't work
                    time.sleep(1 / UPDATES_PER_SECOND)

        except Exception:
            traceback.print_exc()
            # Show console if hidden
            self._toggle_console(True)
            error_occurred = True

        finally:
            # Ensure threads are safely shut down
            self.stop_tracking()
            print('[Hub] Queue handler shut down.')

            # Force shut down the GUI
            if self.use_gui:
                if self._p_gui.is_alive():
                    print('[Hub] Terminating GUI...')
                    self._p_gui.terminate()
                    self._p_gui.join()
                    print('[Hub] GUI shut down')
                self._q_gui.cancel_join_thread()

        if error_occurred:
            print('The above traceback has caused the application to shut down, please consider reporting it.')
            input('Press enter to exit...')

        print('[Hub] Application exit')
