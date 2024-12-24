import multiprocessing
import traceback

from .. import ipc



def process_data(q_send: multiprocessing.Queue, q_receive: multiprocessing.Queue):
    while True:
        received_data = q_receive.get()

        match received_data.type:
            case ipc.Type.Exit:
                print('Shutting down processing process...')
                return

            case ipc.Type.Ping:
                print(f'Background thread received ping with data {received_data.data}')

            case ipc.Type.Raise:
                raise ValueError('test exception')


def run(q_send: multiprocessing.Queue, q_receive: multiprocessing.Queue):
    try:
        process_data(q_send, q_receive)
    # Catch error after KeyboardInterrupt
    except EOFError:
        return

    except Exception as e:
        q_send.put(ipc.QueueItem(ipc.Target.Hub, ipc.Type.Traceback, (e, traceback.format_exc())))
