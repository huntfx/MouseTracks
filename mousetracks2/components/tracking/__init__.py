import time
from itertools import count

from . import utils
from .. import ipc


UPDATES_PER_SECOND = 60


def track(q_send, q_receive):
    for tick in count():
        with utils.RefreshRateLimiter(UPDATES_PER_SECOND) as limiter:

            # Process messages from the queue
            while not q_receive.empty():
                received_message = q_receive.get()
                print(f'Tracking received message: {received_message}')

            # Send a ping (for debugging)
            if not tick % UPDATES_PER_SECOND:
                q_send.put(ipc.QueueItem(ipc.Target.Hub, ipc.Type.Ping, tick))

            # Send a self ping (for debugging)
            if not tick % (UPDATES_PER_SECOND * 10):
                q_send.put(ipc.QueueItem(ipc.Target.Tracking, ipc.Type.Ping, tick))
