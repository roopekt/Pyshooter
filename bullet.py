import pymunk
from pymunk import Vec2d
import messages

MAX_RADIUS = 0.3
SPAWN_OFFSET = 0.5 # offset from the center of player
SPEED = 10

class ServerBullet:

    def __init__(self, shoot_message: messages.ShootMessage, shooter_id: messages.ObjectId):
        self.id = messages.get_new_object_id()
        self.shooter_id = shooter_id
        self.radius = shoot_message.relative_size * MAX_RADIUS

        shoot_direction = (shoot_message.mouse_position_world_space - shoot_message.player_position).normalized()
        initial_position = shoot_message.player_position + shoot_direction * SPAWN_OFFSET
        self.velocity = SPEED * shoot_direction

        self.physics_body = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
        self.physics_body.position = initial_position
        self.collider = pymunk.Circle(self.physics_body, radius=self.radius)

    def update_position(self, delta_time):
        self.physics_body.position += self.velocity * delta_time

    def get_state_update_message(self):
        return messages.BulletStateUpdate(
            bullet_id = self.id,
            position = self.physics_body.position,
            radius = self.radius
        )

class ClientBullet:

    def __init__(self, position: Vec2d, radius: float):
        self.position = position
        self.radius = radius

    def update_state(self, update_message: messages.BulletStateUpdate):
        self.position = update_message.position
