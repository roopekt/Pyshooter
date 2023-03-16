import pymunk
from pymunk import Vec2d
import messages
from .camera import Camera
import pygame
from objectid import ObjectId, get_new_object_id

MAX_RADIUS = 0.3
SPAWN_OFFSET = 0.5 # offset from the center of player
SPEED = 20
MAX_TRAVEL_DISTANCE = 200
MAX_DAMAGE = 1

class ServerBullet:

    def __init__(self, shoot_message: messages.ShootMessage, shooter_id: messages.ObjectId, physics_world: pymunk.Space):
        self.id = get_new_object_id()
        self.shooter_id = shooter_id
        self.radius = shoot_message.relative_size * MAX_RADIUS
        self.damage = shoot_message.relative_size**2 * MAX_DAMAGE

        shoot_direction = (shoot_message.mouse_position_world_space - shoot_message.player_position).normalized()
        self.initial_position = shoot_message.player_position + shoot_direction * SPAWN_OFFSET
        self.velocity = SPEED * shoot_direction

        self.physics_body = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
        self.physics_body.position = self.initial_position
        self.collider = pymunk.Circle(self.physics_body, radius=self.radius)
        self.collider.sensor = True
        self.collider.type = ServerBullet
        self.collider.object_id = self.id
        physics_world.add(self.physics_body, self.collider)

    def update_position(self, delta_time):
        self.physics_body.position += self.velocity * delta_time

    def get_state_update_message(self):
        return messages.BulletStateUpdate(
            bullet_id = self.id,
            position = self.physics_body.position,
            radius = self.radius
        )
    
    def should_be_destroyed(self):
        travel_distance_squared = Vec2d.get_dist_sqrd(self.initial_position, self.physics_body.position)
        return travel_distance_squared > MAX_TRAVEL_DISTANCE**2

class ClientBullet:

    def __init__(self, position: Vec2d, radius: float):
        self.position = position
        self.radius = radius

    def update_state(self, update_message: messages.BulletStateUpdate):
        self.position = update_message.position

    def render(self, camera: Camera):
        pygame.draw.circle(
            camera.window,
            pygame.Color("black"),
            camera.get_screen_position(self.position),
            self.radius * camera.get_graphical_scale_factor()
        )
