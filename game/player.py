import pymunk
from pymunk import Vec2d
import messages
from dataclasses import dataclass, field
from .camera import Camera
import pygame
from . import arenaprops
import math
import mymath
import random
from pygame import freetype
from . import playercolor

RADIUS = 0.5
RECOIL_STRENGTH = 13
RECOIL_EXPONENT = 1.2
MAX_HEALTH = 5

ALMOST_DEAD_COLOR = pygame.Color(128, 128, 128)
DEAD_COLOR = pygame.Color("black")

freetype.init()
PLAYER_LABEL_FONT = freetype.SysFont("calibri", 15)
PLAYER_LABEL_OFFSET = Vec2d(0, 1)

class ServerPlayer:
    
    def __init__(self, id: messages.ObjectId, physics_world: pymunk.Space):
        self.id = id
        self.name = ""
        self.mouse_position_world_space = Vec2d.zero()
        self.health = MAX_HEALTH

        angle = random.random() * math.tau
        spawn_position = Vec2d(arenaprops.PLAYER_SPAWN_RADIUS, 0).rotated(angle)

        self.physics_body = pymunk.Body(body_type=pymunk.Body.DYNAMIC, mass=1, moment=float("inf"))
        self.physics_body.position = spawn_position
        self.collider = pymunk.Circle(self.physics_body, radius=RADIUS)
        self.collider.elasticity = 0.2
        self.collider.friction = 0.5
        self.collider.type = ServerPlayer
        self.collider.object_id = self.id
        physics_world.add(self.physics_body, self.collider)

    def get_position_update_message(self):
        return messages.PlayerStateUpdate(
            player_id = self.id,
            position = self.physics_body.position,
            health = self.health,
            mouse_position_world_space = self.mouse_position_world_space
        )

    def apply_recoil(self, shoot_message: messages.ShootMessage):
        shoot_direction = (shoot_message.mouse_position_world_space - shoot_message.player_position).normalized()
        impulse = -shoot_message.relative_size**RECOIL_EXPONENT * RECOIL_STRENGTH * shoot_direction
        self.physics_body.apply_impulse_at_local_point(impulse)

    def change_health(self, health_change):
        self.health += health_change
        self.health = mymath.clampf(self.health, -1e6, MAX_HEALTH)

@dataclass
class ClientPlayer:
    is_owned_by_client: bool # true if this is the avatar of the client of this machine
    position: Vec2d = field(default_factory=Vec2d.zero)
    health: float = MAX_HEALTH
    mouse_position_world_space: Vec2d = field(default_factory=Vec2d.zero)
    name: str = ""

    def update_state(self, update_message: messages.PlayerStateUpdate):
        self.position = update_message.position
        self.health = update_message.health

        if not self.is_owned_by_client:
            self.mouse_position_world_space = update_message.mouse_position_world_space

    def render(self, camera: Camera):
        graphic_scaler = camera.get_graphical_scale_factor()

        if self.health > 0:
            t = mymath.clampf(self.health / MAX_HEALTH, 0, 1)
            alive_color = playercolor.get_pygame_color(self.name)
            player_color = ALMOST_DEAD_COLOR.lerp(alive_color, t)
        else:
            player_color = DEAD_COLOR

        #body
        pygame.draw.circle(
            camera.window_container.window,
            player_color,
            camera.get_screen_position(self.position),
            RADIUS * graphic_scaler
        )

        #gun
        if self.is_alive():
            offset = self.mouse_position_world_space - self.position
            offset = Vec2d(0, 0) if offset.length < 1e-9 else offset.scale_to_length(RADIUS)
            gun_pos = self.position + offset
            
            pygame.draw.circle(
                camera.window_container.window,
                pygame.Color(255, 255, 0),
                camera.get_screen_position(gun_pos),
                RADIUS * graphic_scaler / 3
            )

        #name label
        label_pos = camera.get_screen_position(self.position + PLAYER_LABEL_OFFSET)
        label_rect = PLAYER_LABEL_FONT.get_rect(self.name)
        label_pos -= pygame.Vector2(label_rect.width / 2, 0)
        PLAYER_LABEL_FONT.render_to(
            camera.window_container.window,
            label_pos,
            self.name,
            fgcolor=pygame.Color("black")
        )

    def is_alive(self):
        return self.health > 0
