import multiprocessing
import traceback

from .. import ipc



def process_data(q_send: multiprocessing.Queue, q_type: ipc.Type, q_data: any = None) -> bool:
    """Process an item of data."""
    match q_type:
        case ipc.Type.Exit:
            print('Shutting down processing process...')
            return False

        case ipc.Type.Raise:
            raise ValueError('test exception')

        case ipc.Type.MouseMove:
            print(f'Mouse has moved to {q_data}')

        case ipc.Type.MouseClick:
            print(f'Mouse button {q_data} clicked')

        case ipc.Type.MouseDoubleClick:
            print(f'Mouse button {q_data} double clicked')

    return True


def run(q_send: multiprocessing.Queue, q_receive: multiprocessing.Queue):
    try:
        while True:
            received_data = q_receive.get()
            if not process_data(q_send, received_data.type, received_data.data):
                return

    # Catch error after KeyboardInterrupt
    except EOFError:
        return

    except Exception as e:
        q_send.put(ipc.QueueItem(ipc.Target.Hub, ipc.Type.Traceback, (e, traceback.format_exc())))
