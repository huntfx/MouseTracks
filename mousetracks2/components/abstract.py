import multiprocessing
import traceback

from . import ipc
from ..exceptions import ExitRequest


class Component:
    def __init__(self, q_send: multiprocessing.Queue, q_receive: multiprocessing.Queue) -> None:
        self.q_send = q_send
        self.q_receive = q_receive
        self.__post_init__()

    def __post_init__(self) -> None:
        """Call this after running `__init__`."""

    @property
    def name(self) -> str:
        """Get the component name."""
        return type(self).__name__

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

    def send_data(self, message: ipc.Message) -> None:
        self.q_send.put(message)

    def receive_data(self):
        return self.q_receive.get()

    def run(self):
        """Run the component."""

    def on_exit(self):
        """Clean up any threads on exit."""

    @classmethod
    def launch(cls, q_send: multiprocessing.Queue, q_receive: multiprocessing.Queue):
        self = cls(q_send, q_receive)

        print(f'[{self.name}] Loaded.')

        try:
            self.run()

        except ExitRequest:
            print(f'[{self.name}] Shut down.')

        # Catch error after KeyboardInterrupt
        except EOFError:
            print(f'[{self.name}] Force shut down.')
            return

        except Exception as e:
            self.send_data(ipc.Traceback(e, traceback.format_exc()))
            print(f'[{self.name}] Error shut down: {e}')

        finally:
            self.on_exit()

        self.send_data(ipc.ProcessShutDownNotification(self.target))
        print(f'[{self.name}] Sent process closed notification.')
