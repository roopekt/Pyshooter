from dataclasses import dataclass
from abc import ABC

class MessageToServer(ABC):
    pass

class MessageToClient(ABC):
    pass

@dataclass
class PlayerConnectionMessage(MessageToServer):
    ip: str

@dataclass
class TempMessage(MessageToClient):
    value: float

@dataclass
class TempReliableToServer(MessageToServer):
    new_value: float
