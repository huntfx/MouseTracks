import multiprocessing
import traceback

from .. import ipc



def process_data(q_send: multiprocessing.Queue, q_type: ipc.Type, q_data: any = None):
    match q_type:
        case ipc.Type.Exit:
            print('Shutting down processing process...')
            return

        case ipc.Type.Ping:
            print(f'Background thread received ping with data {q_data}')

        case ipc.Type.Raise:
            raise ValueError('test exception')


def run(q_send: multiprocessing.Queue, q_receive: multiprocessing.Queue):
    try:
        while True:
            received_data = q_receive.get()
            process_data(q_send, received_data.type, received_data.data)

    # Catch error after KeyboardInterrupt
    except EOFError:
        return

    except Exception as e:
        q_send.put(ipc.QueueItem(ipc.Target.Hub, ipc.Type.Traceback, (e, traceback.format_exc())))
