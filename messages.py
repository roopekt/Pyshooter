from dataclasses import dataclass
from abc import ABC
from pymunk import Vec2d
from objectid import ObjectId
from typing import Optional

class MessageToServer(ABC):
    pass

class MessageToClient(ABC):
    pass

@dataclass
class MessageToServerWithId:
    sender_id: ObjectId
    payload: MessageToServer

# actual messages:

@dataclass
class MousePositionUpdate(MessageToServer):
    mouse_position_world_space: Vec2d

@dataclass
class PlayerStateUpdate(MessageToClient):
    player_id: ObjectId
    position: Vec2d
    health: float
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

@dataclass
class EnterLobbyMessage(MessageToServer):
    player_name: str

@dataclass
class GameStartRequest(MessageToServer):
    pass

@dataclass
class LobbyStateUpdate(MessageToClient):
    connected_player_names: list[str]
    time_to_game_start: Optional[float]

@dataclass
class WallUpdate:
    position: Vec2d
    dimensions: Vec2d
    health: float
    max_health: float
@dataclass
class ArenaUpdate(MessageToClient):
    wall_updates: dict[ObjectId, WallUpdate]
