import multiprocessing
import os
import queue
import sys

from PySide6 import QtCore, QtGui, QtWidgets

from .utils import ICON_PATH
from .main_window import MainWindow
from .. import ipc
from ..abstract import Component
from ...config import GlobalConfig


class QueueWorker(QtCore.QObject):
    """Worker for polling the queue in a background thread."""

    message_received = QtCore.Signal(ipc.Message)

    def __init__(self, queue: multiprocessing.Queue) -> None:
        super().__init__()
        self.queue = queue
        self.running = True

    def run(self) -> None:
        """Continuously poll the queue for messages."""
        while True:
            try:
                message = self.queue.get(timeout=1)
            except queue.Empty:
                if self.running:
                    continue
                break
            self.message_received.emit(message)

    def stop(self) -> None:
        """Stop the worker."""
        self.running = False


class GUI(Component):
    def __post_init__(self) -> None:
        """Setup the threads."""
        self.error: Exception | None = None

        self.receiver_thread = QtCore.QThread()
        self.receiver_worker = QueueWorker(self.q_receive)
        self.receiver_worker.moveToThread(self.receiver_thread)
        self.receiver_thread.started.connect(self.receiver_worker.run)
        self.receiver_thread.finished.connect(self.receiver_worker.deleteLater)

    def on_exit(self) -> None:
        """Safely exit the threads."""
        self.receiver_thread.quit()
        self.receiver_thread.wait()
        self.receiver_worker.stop()

    def exception_raised(self, exc: Exception) -> None:
        """Force the application to shut down when an error is raised.
        This is to match the other components.
        """
        self.error = exc
        QtWidgets.QApplication.exit(1)

    def run(self) -> None:
        """Launch the application."""
        app = QtWidgets.QApplication(sys.argv)
        app.setStyle('Fusion')

        # Register app so that setting an icon is possible
        if os.name == 'nt':
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('uk.huntfx.mousetracks')
        app.setWindowIcon(QtGui.QIcon(ICON_PATH))

        # Setup the window
        win = MainWindow(self)
        if not GlobalConfig().minimise_on_start:
            win.maximise()
        self.receiver_worker.message_received.connect(win.process_message)
        win.exception_raised.connect(self.exception_raised)

        # Start the application
        win.start_tracking()
        self.receiver_thread.start()

        retcode = app.exec()
        match retcode:
            case 0:
                self.send_data(ipc.Exit())
            case 1:
                if self.error is not None:
                    raise self.error
                raise RuntimeError('[GUI] Unexpected shutdown.')
            case _:
                raise RuntimeError('[GUI] Unknown exit code.')
