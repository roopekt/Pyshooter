from dataclasses import dataclass
from abc import ABC
from pymunk import Vec2d
from typing import NewType
from random import randint

PlayerId = NewType("PlayerId", int)
def get_new_player_id():
    return PlayerId(randint(0, 0xFF_FF_FF_FF))

class MessageToServer(ABC):
    pass

class MessageToClient(ABC):
    pass

@dataclass
class MessageToServerWithId:
    sender_id: PlayerId
    payload: MessageToServer

@dataclass
class MousePositionUpdate(MessageToServer):
    mouse_position_world_space: Vec2d

@dataclass
class PlayerStateUpdate(MessageToClient):
    player_id: PlayerId
    position: Vec2d
    mouse_position_world_space: Vec2d
