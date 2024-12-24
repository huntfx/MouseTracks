"""Standard format for data to be sent through communication queues."""

from dataclasses import dataclass
from enum import Enum, auto


class Target(Enum):
    """System components that can send or receive messages."""
    Hub = auto()
    Tracking = auto()


class Type(Enum):
    """Message types exchanged between components."""
    Ping = auto()


@dataclass
class QueueItem:
    """Represents an item to be passed through a communication queue.

    Attributes:
        target: The intended recipient component of the message.
        type: The type of message being sent.
        data: Optional data payload associated with the message.
    """
    target: Target
    type: Type
    data: any = None
