from dataclasses import dataclass
from abc import ABC
from pymunk import Vec2d
from typing import NewType
from random import randbytes

ObjectId = NewType("ObjectId", int)
def get_new_object_id():
    return ObjectId(int.from_bytes(randbytes(4), "big"))

class MessageToServer(ABC):
    pass

class MessageToClient(ABC):
    pass

@dataclass
class MessageToServerWithId:
    sender_id: ObjectId
    payload: MessageToServer

@dataclass
class MousePositionUpdate(MessageToServer):
    mouse_position_world_space: Vec2d

@dataclass
class PlayerStateUpdate(MessageToClient):
    player_id: ObjectId
    position: Vec2d
    mouse_position_world_space: Vec2d

@dataclass
class ShootMessage(MessageToServer):
    player_position: Vec2d
    mouse_position_world_space: Vec2d
    relative_size: float

@dataclass
class BulletStateUpdate(MessageToClient):
    bullet_id: ObjectId
    position: Vec2d
    radius: float

@dataclass
class BulletDestroyMessage(MessageToClient):
    bullet_id: ObjectId
