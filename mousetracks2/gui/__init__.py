from enum import Enum, auto
from Qt import QtCore, QtWidgets, QtGui
from threading import Thread
from vfxwindow import VFXWindow

from constants import *


class MainWindow(VFXWindow):
    """Window used to wrap the main program.
    This does not directly do any tracking, it is just meant as an
    interface to the script itself.

    Communication:
        Every time an option is chosen in the GUI, a corresponding
        command is added to the queue. The thread will read the queue
        in a "first in first out" method. If the thread is "paused",
        then it will still read all commands, but it may ignore some.
        The queue contains instances of `GUICommand`.

        The thread in return will send data back by using the
        `receiveFromThread` method. Instead of using a queue, the GUI
        will instantly execute the command. This uses instances of
        `ThreadEvent`.
    """

    def __init__(self, func, **kwargs):
        super().__init__(**kwargs)
        self._function = func

        # Setup layout
        # This is a design meant for debugging purposes
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

        horizontal = QtWidgets.QHBoxLayout()
        horizontal.addWidget(QtWidgets.QLabel('Total Mouse Distance:'))
        self.distance = QtWidgets.QLabel('0.0')
        horizontal.addWidget(self.distance)
        layout.addLayout(horizontal)

        horizontal = QtWidgets.QHBoxLayout()
        horizontal.addWidget(QtWidgets.QLabel('Current Mouse Speed:'))
        self.speed = QtWidgets.QLabel('0.0')
        horizontal.addWidget(self.speed)
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
        This is for display purposes only.

        Parameters:
            state (ThreadState): State of the thread.
                It can be Running, Paused or Stopped.
        """
        self._state = state
        self.status.setText(state.name)

    def thread(self):
        """Get the current running thread.
        If not running, None will be returned.
        """
        if self.state() == ThreadState.Stopped:
            return None
        return self._thread

    def startThread(self):
        """Start the main process in a thread."""
        self.queue = []
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
        if self.thread() is not None:
            self.queue.append(command)
            return True
        return False

    def receiveFromThread(self, event, *data):
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

        elif event == ThreadEvent.MouseMove:
            coordinate = data[0]
            if all(0 >= n >= 1 for n in coordinate):
                pass  # TODO: Draw to QImage

        elif event == ThreadEvent.MouseDistance:
            distance = data[0]
            prefix = ''
            if distance > 100000000:
                distance /= 1000000
                prefix = 'M'
            elif distance > 100000:
                distance /= 1000
                prefix = 'K'
            self.distance.setText(str(round(distance, 2)) + prefix)

        elif event == ThreadEvent.MouseSpeed:
            speed = data[0]
            self.speed.setText(str(round(speed, 2)))

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
        """Send a command to raise an exception.
        For testing purposes only.
        """
        self.sendToThread(GUICommand.RaiseException)
