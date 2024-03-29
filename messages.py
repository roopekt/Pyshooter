from dataclasses import dataclass
from abc import ABC
from pymunk import Vec2d
from objectid import ObjectId
from typing import Optional

class MessageToServer(ABC):
    pass

class MessageToClient(ABC):
    pass

class LobbyMessage(ABC):
    pass

class GameMessage(ABC):
    pass

@dataclass
class MessageToServerWithId:
    sender_id: ObjectId
    payload: MessageToServer

# actual messages:

@dataclass
class MousePositionUpdate(MessageToServer, GameMessage):
    mouse_position_world_space: Vec2d

@dataclass
class PlayerStateUpdate(MessageToClient, GameMessage):
    player_id: ObjectId
    health: float
    mouse_position_world_space: Vec2d
    head_orientation: float
    head_position:      Vec2d
    left_leg_position:  Vec2d
    right_leg_position: Vec2d
    left_arm_position:  Vec2d
    right_arm_position: Vec2d

@dataclass
class ShootMessage(MessageToServer, GameMessage):
    initial_bullet_position: Vec2d
    mouse_position_world_space: Vec2d
    relative_size: float

@dataclass
class BulletStateUpdate(MessageToClient, GameMessage):
    bullet_id: ObjectId
    position: Vec2d
    radius: float

@dataclass
class BulletDestroyMessage(MessageToClient, GameMessage):
    bullet_id: ObjectId

@dataclass
class WallUpdate:
    position: Vec2d
    dimensions: Vec2d
    health: float
    max_health: float
@dataclass
class ArenaUpdate(MessageToClient, GameMessage):
    wall_updates: dict[ObjectId, WallUpdate]

@dataclass
class JoinGameMessage(MessageToServer, GameMessage):
    player_name: str

@dataclass
class NewPlayerNotification(MessageToClient, GameMessage):
    player_id: ObjectId
    player_name: str

@dataclass
class GoToLobbyRequest(MessageToServer, GameMessage):
    pass

@dataclass
class GoToLobbyNotification(MessageToClient, GameMessage):
    pass

@dataclass
class EnterLobbyMessage(MessageToServer, LobbyMessage):
    player_name: str

@dataclass
class GameStartRequest(MessageToServer, LobbyMessage):
    pass

@dataclass
class LobbyStateUpdate(MessageToClient, LobbyMessage):
    connected_player_names: list[str]
    time_to_game_start: Optional[float]
