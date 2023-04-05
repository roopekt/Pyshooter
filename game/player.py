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
from .sprite import Sprite
from objectid import ObjectId

RECOIL_STRENGTH = 26
RECOIL_EXPONENT = 1.2
MAX_HEALTH = 5

HEAD_RADIUS = 0.5
LIMB_RADIUS = 0.3
LIMB_STIFFNESS = 120
LIMB_DAMPING = 10

FACE_WIDTH = 1.1
GUN_WIDTH = 3
GUN_OFFSET = Vec2d(.183, -.033) * GUN_WIDTH

ALMOST_DEAD_COLOR = pygame.Color(128, 128, 128)
DEAD_COLOR = pygame.Color("black")

freetype.init()
PLAYER_LABEL_FONT = freetype.SysFont("calibri", 15)
PLAYER_LABEL_OFFSET = Vec2d(0, 1)

@dataclass
class CompletePhysicsBody:
    body: pymunk.Body
    collider: pymunk.Shape

def get_circle_body(position: Vec2d, mass: float, radius: float, rotation_allowed: bool, physics_world: pymunk.Space, id: ObjectId):
        moment = 1.0 if rotation_allowed else float('inf')
        physics_body = pymunk.Body(body_type=pymunk.Body.DYNAMIC, mass=mass, moment=moment)
        physics_body.position = position

        collider = pymunk.Circle(physics_body, radius=radius)
        collider.elasticity = 0.2
        collider.friction = 0.5
        collider.type = ServerPlayer
        collider.object_id = id

        physics_world.add(physics_body, collider)
        return CompletePhysicsBody(physics_body, collider)

class ServerPlayer:
    
    def __init__(self, id: ObjectId, physics_world: pymunk.Space):
        self.id = id
        self.name = ""
        self.mouse_position_world_space = Vec2d.zero()
        self.health = MAX_HEALTH

        angle = random.random() * math.tau
        spawn_position = Vec2d(arenaprops.PLAYER_SPAWN_RADIUS, 0).rotated(angle)

        rv = Vec2d(HEAD_RADIUS + 0.3*LIMB_RADIUS, 0)
        self.head      = get_circle_body(spawn_position,                              1,   HEAD_RADIUS, True,  physics_world, id)
        self.right_leg = get_circle_body(spawn_position + rv.rotated_degrees(-45),    1/4, LIMB_RADIUS, False, physics_world, id)
        self.left_leg  = get_circle_body(spawn_position + rv.rotated_degrees(180+45), 1/4, LIMB_RADIUS, False, physics_world, id)
        self.right_arm = get_circle_body(spawn_position + rv.rotated_degrees(20),     1/4, LIMB_RADIUS, False, physics_world, id)
        self.left_arm  = get_circle_body(spawn_position + rv.rotated_degrees(180-20), 1/4, LIMB_RADIUS, False, physics_world, id)

        self.right_leg_spring = pymunk.DampedSpring(self.head.body, self.right_leg.body, rv.rotated_degrees(-45),    Vec2d.zero(), 0,   LIMB_STIFFNESS,   LIMB_DAMPING)
        self.left_leg_spring  = pymunk.DampedSpring(self.head.body, self.left_leg.body,  rv.rotated_degrees(180+45), Vec2d.zero(), 0,   LIMB_STIFFNESS,   LIMB_DAMPING)
        self.right_arm_spring = pymunk.DampedSpring(self.head.body, self.right_arm.body, rv.rotated_degrees(180-20), Vec2d.zero(), 0,   LIMB_STIFFNESS,   LIMB_DAMPING)
        self.left_arm_spring  = pymunk.DampedSpring(self.head.body, self.left_arm.body,  rv.rotated_degrees(20),     Vec2d.zero(), 0, 2*LIMB_STIFFNESS, 2*LIMB_DAMPING)
        self.left_leg_spring .collide_bodies = False
        self.right_leg_spring.collide_bodies = False
        self.left_arm_spring .collide_bodies = False
        self.right_arm_spring.collide_bodies = False
        physics_world.add(self.left_leg_spring )
        physics_world.add(self.right_leg_spring)
        physics_world.add(self.left_arm_spring )
        physics_world.add(self.right_arm_spring)

    def get_position_update_message(self):
        return messages.PlayerStateUpdate(
            player_id = self.id,
            health = self.health,
            mouse_position_world_space = self.mouse_position_world_space,
            head_orientation = self.head.body.angle,
            head_position = self.head.body.position,
            left_leg_position  = self.left_leg.body .position,
            right_leg_position = self.right_leg.body.position,
            left_arm_position  = self.left_arm.body .position,
            right_arm_position = self.right_arm.body.position
        )

    def apply_recoil(self, shoot_message: messages.ShootMessage):
        shoot_direction = (shoot_message.mouse_position_world_space - shoot_message.initial_bullet_position).normalized()
        impulse = -shoot_message.relative_size**RECOIL_EXPONENT * RECOIL_STRENGTH * shoot_direction

        self.head.body.apply_impulse_at_world_point(    5/10 * impulse, self.head.body.position)
        self.left_arm.body.apply_impulse_at_world_point(5/10 * impulse, self.left_arm.body.position)

    def change_health(self, health_change):
        self.health += health_change
        self.health = mymath.clampf(self.health, -1e6, MAX_HEALTH)

@dataclass
class ClientPlayer:
    is_owned_by_client: bool # true if this is the avatar of the client of this machine
    health: float = MAX_HEALTH
    mouse_position_world_space: Vec2d = field(default_factory=Vec2d.zero)
    name: str = ""
    head_orientation: float = 0
    head_position:      Vec2d = field(default_factory=Vec2d.zero)
    left_leg_position:  Vec2d = field(default_factory=Vec2d.zero)
    right_leg_position: Vec2d = field(default_factory=Vec2d.zero)
    left_arm_position:  Vec2d = field(default_factory=Vec2d.zero)
    right_arm_position: Vec2d = field(default_factory=Vec2d.zero)

    def __post_init__(self):
        self.face_sprite = Sprite("assets/player-face.png", FACE_WIDTH, transparent=True)
        self.gun_sprite = Sprite("assets/rifle.png", GUN_WIDTH, transparent=True)

    def update_state(self, update_message: messages.PlayerStateUpdate):
        self.head_orientation = update_message.head_orientation
        self.head_position = update_message.head_position
        self.left_leg_position = update_message.left_leg_position
        self.right_leg_position = update_message.right_leg_position
        self.left_arm_position = update_message.left_arm_position
        self.right_arm_position = update_message.right_arm_position
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

        #limbs
        limb_positions = (
            self.head_position,
            self.left_leg_position, 
            self.right_leg_position,
            self.left_arm_position, 
            self.right_arm_position
        )
        for limb_position in limb_positions:
            pygame.draw.circle(
                camera.window_container.window,
                player_color,
                camera.get_screen_position(limb_position),
                LIMB_RADIUS * graphic_scaler
            )

        #head
        pygame.draw.circle(
            camera.window_container.window,
            player_color,
            camera.get_screen_position(self.head_position),
            HEAD_RADIUS * graphic_scaler
        )
        self.face_sprite.render(camera, self.head_position, self.head_orientation)

        #gun
        if self.is_alive():
            gun_orientation = (self.mouse_position_world_space - self.left_arm_position).angle
            should_flip = (math.tau/4 < gun_orientation < math.tau/2) or (-math.tau/2 < gun_orientation < -math.tau/4)
            gun_offset = Vec2d(GUN_OFFSET.x, GUN_OFFSET.y * (-1 if should_flip else 1))
            gun_position = self.left_arm_position + gun_offset.rotated(gun_orientation)
            self.gun_sprite.render(camera, gun_position, orientation=gun_orientation, flip_y=should_flip)

        #name label
        label_pos = camera.get_screen_position(self.head_position + PLAYER_LABEL_OFFSET)
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
