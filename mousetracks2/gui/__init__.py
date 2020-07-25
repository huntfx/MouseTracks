from enum import Enum, auto
from Qt import QtCore, QtWidgets, QtGui
from queue import Queue, Empty
from threading import Thread
from vfxwindow import VFXWindow

from constants import *


class MainWindow(VFXWindow):
    def __init__(self, **kwargs):
        self._function = kwargs.pop('func')
        self._ups = kwargs.pop('ups', 60)

        super().__init__(**kwargs)

        # [TEMPORARY] Layout setup
        layout = QtWidgets.QVBoxLayout()
        start = QtWidgets.QPushButton('Start')
        start.clicked.connect(self.startTracking)
        layout.addWidget(start)
        start = QtWidgets.QPushButton('Stop')
        start.clicked.connect(self.stopTracking)
        layout.addWidget(start)
        pause = QtWidgets.QPushButton('Pause/Unpause')
        pause.clicked.connect(self.pauseTracking)
        layout.addWidget(pause)
        crash = QtWidgets.QPushButton('Raise Exception')
        crash.clicked.connect(self.excTracking)
        layout.addWidget(crash)

        horizontal = QtWidgets.QHBoxLayout()
        horizontal.addWidget(QtWidgets.QLabel('Current Status:'))
        self.status = QtWidgets.QLabel()
        horizontal.addWidget(self.status)
        layout.addLayout(horizontal)

        self.setCentralWidget(QtWidgets.QWidget())
        self.centralWidget().setLayout(layout)

        # Window setup
        self.setState(ThreadState.Stopped)

    def closeEvent(self, event):
        """Safely close the thread."""
        if self.thread():
            self.stopTracking()
        return super().closeEvent(event)

    def state(self):
        """Get the current script state."""
        return self._state

    def setState(self, state):
        """Set the new thread state.

        Parameters:
            state (ThreadState): State of the thread.
                It can be Running, Paused or Stopped.
        """
        try:
            oldState = self._state
        except AttributeError:
            oldState = ThreadState.Stopped
        self._state = state
        self.status.setText(state.name)

        if state != oldState:
            print(f'Thread state changed: {state.name}')

    def queue(self):
        """Return the queue for the thread to read."""
        try:
            return self._queue
        except AttributeError:
            self._queue = Queue()
        return self._queue

    def ups(self):
        """Get the number of updates per second."""
        return self._ups

    def thread(self):
        """Get the current running thread.
        If not running, None will be returned.
        """
        if self.state() == ThreadState.Stopped:
            return None
        return self._thread

    def startThread(self):
        """Setup and start a thread."""
        # Empty the queue if needed
        # This is a redundency measure and shouldn't need to run
        while not self.queue().empty():
            try:
                self.queue().get(False)
            except Empty:
                continue

        # Start thread
        self._thread = Thread(target=self._function, args=(self,))
        self._thread.daemon = True
        self._thread.start()

    def sendToThread(self, command):
        """Send a command to the thread.
        If the thread isn't running, the command will be ignored.

        Parameters:
            command (GUICommand): Command to send to thread.

        Returns:
            True if the command was sent, otherwise False.
        """
        if self.thread():
            self.queue().put(command)
            return True
        return False

    def receiveFromThread(self, event, *args, **kwargs):
        """Handle any events sent back from the main thread.

        Parameters:
            event (ThreadEvent): Event received from thread.
        """
        if event == ThreadEvent.Started:
            self.setState(ThreadState.Running)

        elif event == ThreadEvent.Stopped:
            self.setState(ThreadState.Stopped)

        elif event == ThreadEvent.Paused:
            self.setState(ThreadState.Paused)

        elif event == ThreadEvent.Unpaused:
            self.setState(ThreadState.Running)

        elif event == ThreadEvent.Exception:
            self.setState(ThreadState.Stopped)

    @QtCore.Slot()
    def startTracking(self):
        """Start/unpause the script."""
        if self.thread():
            self.sendToThread(GUICommand.Unpause)

        else:
            self.startThread()

    @QtCore.Slot()
    def pauseTracking(self):
        """Pause/unpause the script."""
        self.sendToThread(GUICommand.TogglePause)

    @QtCore.Slot()
    def stopTracking(self):
        """Stop the script."""
        self.sendToThread(GUICommand.Stop)

    @QtCore.Slot()
    def excTracking(self):
        """For testing only, send a command to raise an exception."""
        self.sendToThread(GUICommand.RaiseException)
