import multiprocessing
import os
import time
import traceback
from typing import TYPE_CHECKING, Iterator

import psutil

from . import ipc
from ..exceptions import ExitRequest

if TYPE_CHECKING:
    import multiprocessing.queues


class Component:
    def __init__(self, q_send: multiprocessing.queues.Queue, q_receive: multiprocessing.queues.Queue) -> None:
        self._q_send = q_send
        self._q_recv = q_receive
        self.name = type(self).__name__
        self.__post_init__()
        self._parent_pid = os.getppid()

    def __post_init__(self) -> None:
        """Call this after running `__init__`."""

    @property
    def name(self) -> str:
        """Get the component name."""
        return self._name

    @name.setter
    def name(self, name: str) -> None:
        """Set the component name."""
        self._name = name

    @property
    def target(self) -> int:
        """Get the component target enum."""
        # TODO: Define this in subclasses
        match self.name:
            case 'Tracking':
                return ipc.Target.Tracking
            case 'Processing':
                return ipc.Target.Processing
            case 'AppDetection':
                return ipc.Target.AppDetection
            case 'GUI':
                return ipc.Target.GUI
            case _:
                raise NotImplementedError(self.name)

    def is_hub_running(self) -> bool:
        """Determine if the Hub is still running.
        If it is not running, then attempting to read from a queue will
        lock the entire process.
        """
        return psutil.pid_exists(self._parent_pid)

    def send_data(self, message: ipc.Message) -> None:
        self._q_send.put(message)

    def receive_data(self, polling_rate: float = 0.0) -> Iterator[ipc.Message]:
        """Receive any available data as an iterator.

        Parameters:
            polling_rate: Wait for more data instead of returning.
                If this is set, then the loop will continue, waiting for
                this amount of time before checking for more items.
                If not set, then the loop will run once.

        This does not use timeouts, as the Hub process shutting down
        would cause locks if a read was mid-timeout. Instead, a check
        is first done to ensure the Hub is still running, then a check
        is done if the queue is empty or not. The Hub check is done per
        queue item so that a backlog of commands won't cause issues.
        """
        while True:
            # Trigger an emergecy shutdown if the hub is not running
            if not self.is_hub_running():
                print(f'[{self.name}] Hub not detected, triggering force shutdown...')
                self._q_send.close()
                self._q_recv.close()
                self._q_send.cancel_join_thread()
                self._q_recv.cancel_join_thread()
                yield ipc.Exit()
                return

            # Check if the queue is empty
            if self._q_recv.empty():
                if not polling_rate:
                    return
                time.sleep(polling_rate)
                continue

            # Read from the queue
            message = self._q_recv.get()

            # Intercept message if required, otherwise yield
            match message:
                case ipc.RequestPID():
                    self.send_data(ipc.SendPID(source=self.target, pid=os.getpid()))
                case _:
                    yield message

    def run(self) -> None:
        """Run the component."""

    def on_exit(self) -> None:
        """Clean up any threads on exit.
        If force is set, then just emergency shut down everything.
        """

    @classmethod
    def launch(cls, q_send: multiprocessing.queues.Queue, q_receive: multiprocessing.queues.Queue) -> None:
        # Attempt to initialise the class
        try:
            self = cls(q_send, q_receive)

        # If an error happens on load, then stop here
        # A shutdown is triggered for all other components
        except Exception as e:
            q_send.put(ipc.Traceback(e, traceback.format_exc()))
            self = Component(q_send, q_receive)
            self.name = cls.__name__
            print(f'[{self.name}] Error shut down: {e}')

        # Run the component with extra error handling
        else:
            print(f'[{self.name}] Loaded.')
            self.send_data(ipc.ComponentLoaded(self.target))

            try:
                self.run()

            except ExitRequest:
                print(f'[{self.name}] Shut down.')

            # Catch error after KeyboardInterrupt
            except EOFError:
                print(f'[{self.name}] Force shut down.')
                return

            except Exception as e:
                print(f'[{self.name}] Error shut down: {e}')
                q_send.put(ipc.Traceback(e, traceback.format_exc()))

            finally:
                self.on_exit()

        if self.is_hub_running():
            q_send.put(ipc.ProcessShutDownNotification(self.target))
            print(f'[{self.name}] Sent process closed notification.')
        else:
            print(f'[{self.name}] Process closed due to Hub not running.')
