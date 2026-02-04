import sys
import time
from typing import cast

from PySide6 import QtCore, QtGui, QtWidgets

from . import ipc
from .abstract import Component
from ..gui.utils import ICON_PATH
from ..gui.main_window import MainWindow
from ..gui.splash import SplashScreen
from ..cli import CLI
from ..utils.system import prepare_application_icon


class QueueWorker(QtCore.QObject):
    """Worker for polling the queue in a background thread."""

    message_received = QtCore.Signal(ipc.Message)
    ready = QtCore.Signal()

    def __init__(self, component: Component) -> None:
        super().__init__()
        self.component = component
        self.running = True

    def run(self) -> None:
        """Continuously poll the queue for messages."""
        while True:
            for message in self.component.receive_data():
                self.message_received.emit(message)
                match message:
                    case ipc.Exit():
                        return
                    case ipc.AllComponentsLoaded():
                        self.ready.emit()

            time.sleep(0.01)

            if not self.running:
                break

    def stop(self) -> None:
        """Stop the worker."""
        self.running = False


class GUI(Component):
    def __post_init__(self) -> None:
        """Setup the threads."""
        self.error: Exception | None = None

        # Setup the QApplication
        app = QtWidgets.QApplication(sys.argv)
        app.setStyle('Fusion')

        prepare_application_icon(ICON_PATH)
        app.setWindowIcon(QtGui.QIcon(ICON_PATH))

        self.receiver_thread = QtCore.QThread()
        self.receiver_worker = QueueWorker(self)
        self.receiver_worker.moveToThread(self.receiver_thread)
        self.receiver_thread.started.connect(self.receiver_worker.run)
        self.receiver_thread.finished.connect(self.receiver_worker.deleteLater)

        # Show a splash screen while loading
        if not CLI.disable_splash:
            QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.CursorShape.WaitCursor)
            self._splash = SplashScreen()
            self.receiver_worker.ready.connect(self._splash.close)
            self.receiver_worker.ready.connect(QtWidgets.QApplication.restoreOverrideCursor)

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
        app = QtWidgets.QApplication.instance()
        if app is None:
            app = QtWidgets.QApplication(sys.argv)
        app = cast(QtWidgets.QApplication, app)

        # Setup the window
        win = MainWindow(self)
        app.setActiveWindow(win)
        app.commitDataRequest.connect(win.handle_session_shutdown)
        self.receiver_worker.message_received.connect(win.process_message)
        win.exception_raised.connect(self.exception_raised)
        self.receiver_thread.start()

        # Run the application
        retcode = app.exec()

        # Trigger a shutdown of all the other components
        if self.is_hub_running():
            self.send_data(ipc.ToggleConsole(True))
            match retcode:
                case 0:
                    self.send_data(ipc.Exit())
                case 1:
                    if self.error is not None:
                        raise self.error
                    raise RuntimeError('[GUI] Unexpected shutdown.')
                case _:
                    raise RuntimeError('[GUI] Unknown exit code.')
