import pymunk
from pymunk import Vec2d
import messages
from dataclasses import dataclass, field
from typing import Optional

RADIUS = 0.5
RECOIL_STRENGTH = 8

@dataclass
class ClientPlayer:
    is_owned_by_client: bool # true if this is the avatar of the client of this machine
    position: Optional[Vec2d] = None
    mouse_position_world_space: Vec2d = field(default_factory=Vec2d.zero)

    def update_state(self, update_message: messages.PlayerStateUpdate):
        self.position = update_message.position

        if not self.is_owned_by_client:
            self.mouse_position_world_space = update_message.mouse_position_world_space

class ServerPlayer:
    
    def __init__(self, id: messages.ObjectId, physics_world: pymunk.Space):
        self.id = id
        self.mouse_position_world_space = Vec2d.zero()

        self.physics_body = pymunk.Body(body_type=pymunk.Body.DYNAMIC)
        self.physics_body.position = Vec2d(0, 5)
        self.collider = pymunk.Circle(self.physics_body, radius=RADIUS)
        self.collider.density = 1
        self.collider.elasticity = 0.8
        physics_world.add(self.physics_body, self.collider)

    def get_position_update_message(self):
        return messages.PlayerStateUpdate(
            player_id = self.id,
            position = self.physics_body.position,
            mouse_position_world_space = self.mouse_position_world_space
        )

    def apply_recoil(self, shoot_message: messages.ShootMessage):
        shoot_direction = (shoot_message.mouse_position_world_space - shoot_message.player_position).normalized()
        impulse = -shoot_message.relative_size**2 * RECOIL_STRENGTH * shoot_direction
        self.physics_body.apply_impulse_at_local_point(impulse)