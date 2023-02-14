from dataclasses import dataclass
from abc import ABC
from typing import NewType, Optional
from random import randbytes

PlayerId = NewType("PlayerId", int)
def get_new_player_id():
    return PlayerId(int(randbytes(4)))

class MessageToServer(ABC):
    pass

class MessageToClient(ABC):
    pass

@dataclass
class MessageToServerWithId:
    sender_id: PlayerId
    payload: MessageToServer

@dataclass
class PlayerConnectionMessage(MessageToServer):
    pass

@dataclass
class TempMessage(MessageToClient):
    value: float

@dataclass
class TempReliableToServer(MessageToServer):
    new_value: float
