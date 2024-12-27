from enum import Enum, auto
from PySide6 import QtCore, QtWidgets, QtGui
from threading import Thread
import sys
import queue
from .. import ipc
from ...utils.math import calculate_line, calculate_distance
from ...utils.win import cursor_position


class QueueWorker(QtCore.QObject):
    """Worker for polling the queue in a background thread."""
    message_received = QtCore.Signal(object)  # Signal to send received data

    def __init__(self, queue):
        super().__init__()
        self.queue = queue
        self.running = True

    def run(self):
        """Continuously poll the queue for messages."""
        while True:
            try:
                message = self.queue.get(timeout=1)
            except queue.Empty:
                if self.running:
                    continue
                break
            self.message_received.emit(message)

    def stop(self):
        """Stop the worker."""
        self.running = False


class MainWindow(QtWidgets.QMainWindow):
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
    update_pixel = QtCore.Signal(int, int, QtGui.QColor)

    def __init__(self, q_send, q_receive, **kwargs):
        super().__init__(**kwargs)
        self.q_send = q_send
        self.q_receive = q_receive

        self.mouse_distance = 0
        self.mouse_speed = 0
        self.mouse_position = cursor_position()
        self.mouse_move_tick = 0

        # Setup layout
        # This is a design meant for debugging purposes
        layout = QtWidgets.QVBoxLayout()
        start = QtWidgets.QPushButton('Start')
        start.clicked.connect(self.startTracking)
        layout.addWidget(start)
        start = QtWidgets.QPushButton('Stop')
        start.clicked.connect(self.stopTracking)
        layout.addWidget(start)
        pause = QtWidgets.QPushButton('Pause')
        pause.clicked.connect(self.pauseTracking)
        layout.addWidget(pause)
        crash = QtWidgets.QPushButton('Raise Exception (tracking)')
        crash.clicked.connect(self.raiseTracking)
        layout.addWidget(crash)
        crash = QtWidgets.QPushButton('Raise Exception (processing)')
        crash.clicked.connect(self.raiseProcessing)
        layout.addWidget(crash)
        crash = QtWidgets.QPushButton('Raise Exception (hub)')
        crash.clicked.connect(self.raiseHub)
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

        # Create a label to display the pixmap
        self.image_label = QtWidgets.QLabel()
        #self.image_label.setFixedSize(width, height)
        layout.addWidget(self.image_label)
        # Create a QPixmap and QImage
        self.pixmap = QtGui.QPixmap(360, 240)
        self.pixmap.fill(QtCore.Qt.white)  # Start with a white background
        self.image_label.setPixmap(self.pixmap)
        self.image = self.pixmap.toImage()
        self.update_pixel.connect(self.update_pixmap_pixel)

        self.setCentralWidget(QtWidgets.QWidget())
        self.centralWidget().setLayout(layout)

        # Window setup
        self.setState('stopped')

        # Start queue worker
        self.queue_thread = QtCore.QThread()
        self.queue_worker = QueueWorker(q_receive)
        self.queue_worker.moveToThread(self.queue_thread)

        # Connect signals and slots
        self.queue_worker.message_received.connect(self.processMessage)
        self.queue_thread.started.connect(self.queue_worker.run)
        self.queue_thread.finished.connect(self.queue_worker.deleteLater)

        # Start the thread
        self.queue_thread.start()

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
        self.status.setText(state)

    def processMessage(self, message: ipc.Message):
        match message:
            case ipc.MouseMove():
                distance_to_previous = calculate_distance(message.position, self.mouse_position)
                if message.tick == self.mouse_move_tick + 1:
                    self.mouse_speed = distance_to_previous
                self.mouse_distance += distance_to_previous

                self.distance.setText(str(int(self.mouse_distance)))
                self.speed.setText(str(int(self.mouse_speed)))

                self.mouse_position = message.position
                self.mouse_move_tick = message.tick

                # remap to 1440p (hardcoded for now)
                if 0 <= message.position[0] < 2560 and 0 <= message.position[1] < 1440:
                    x = message.position[0] * self.image.width() / 2560
                    y = message.position[1] * self.image.height() / 1440
                    self.update_pixel.emit(x, y, QtCore.Qt.black)

    @QtCore.Slot()
    def startTracking(self):
        """Start/unpause the script."""
        self.q_send.put(ipc.TrackingState(ipc.TrackingState.State.Start))

    @QtCore.Slot()
    def pauseTracking(self):
        """Pause/unpause the script."""
        self.q_send.put(ipc.TrackingState(ipc.TrackingState.State.Pause))

    @QtCore.Slot()
    def stopTracking(self):
        """Stop the script."""
        self.q_send.put(ipc.TrackingState(ipc.TrackingState.State.Stop))

    @QtCore.Slot()
    def raiseTracking(self):
        """Send a command to raise an exception.
        For testing purposes only.
        """
        self.q_send.put(ipc.DebugRaiseError(ipc.Target.Tracking))

    @QtCore.Slot()
    def raiseProcessing(self):
        """Send a command to raise an exception.
        For testing purposes only.
        """
        self.q_send.put(ipc.DebugRaiseError(ipc.Target.Processing))

    @QtCore.Slot()
    def raiseHub(self):
        """Send a command to raise an exception.
        For testing purposes only.
        """
        self.q_send.put(ipc.DebugRaiseError(ipc.Target.Hub))

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        """Send a signal that the GUI has closed."""
        self.queue_worker.stop()
        self.q_send.put(ipc.Exit())
        self.queue_thread.quit()
        self.queue_thread.wait()
        super().closeEvent(event)

    @QtCore.Slot(int, int, QtGui.QColor)
    def update_pixmap_pixel(self, x: int, y: int, colour: QtGui.QColor):
        """Update a specific pixel in the QImage and refresh the display."""
        self.image.setPixelColor(x, y, colour)

        self.pixmap.convertFromImage(self.image)
        self.image_label.setPixmap(self.pixmap)


def run(q_send, q_receive):
    app = QtWidgets.QApplication(sys.argv)
    m = MainWindow(q_send, q_receive)
    m.show()
    app.exec()
