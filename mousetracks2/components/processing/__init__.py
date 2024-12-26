import multiprocessing
import traceback

from .. import ipc



def process_data(q_send: multiprocessing.Queue, message: ipc.Message) -> bool:
    """Process an item of data."""
    match message:
        case ipc.MouseMove():
            print(f'[Processing] Mouse has moved to {message.position}')

        case ipc.MouseClick(double=True):
            print(f'[Processing] Mouse button {message.button} double clicked')

        case ipc.MouseClick():
            print(f'[Processing] Mouse button {message.button} clicked')

        case ipc.DebugRaiseError():
            raise RuntimeError('test exception')

        case ipc.TrackingState(state=ipc.TrackingState.State.Stop):
            print('[Processing] Shut down.')
            return False

    return True


def run(q_send: multiprocessing.Queue, q_receive: multiprocessing.Queue) -> None:
    print('[Processing] Loaded.')

    try:
        while True:
            if not process_data(q_send, q_receive.get()):
                return

    # Catch error after KeyboardInterrupt
    except EOFError:
        return

    except Exception as e:
        q_send.put(ipc.Traceback(e, traceback.format_exc()))
