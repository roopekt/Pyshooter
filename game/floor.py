import pymunk
from pymunk import Vec2d
from .camera import Camera
import pygame

VERTEX_A = Vec2d(-1000, 0)
VERTEX_B = Vec2d(1000, 0)

class ServerFloor:

    def __init__(self, world: pymunk.Space):
        self.body = pymunk.Body(body_type=pymunk.Body.STATIC, mass=1)
        self.collider = pymunk.Segment(self.body, (-1000, 0), (1000, 0), radius=0)
        self.collider.elasticity = 0
        self.collider.friction = 0.5
        world.add(self.body, self.collider)

class ClientFloor:

    def render(self, camera: Camera):
        pygame.draw.line(
            camera.window,
            pygame.Color("black"),
            camera.get_screen_position(VERTEX_A),
            camera.get_screen_position(VERTEX_B),
            width = 2
        )

