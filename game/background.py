from .sprite import Sprite
from .camera import Camera
import pygame
import mymath
from pymunk import Vec2d
from math import ceil, isnan

TILE_WIDTH = 15

class Background:

    def __init__(self):
        self.tile = Sprite("assets/brick-wall.jpg", TILE_WIDTH, pivot = "corner")

    def render(self, camera: Camera):
        tile_size = Vec2d(
            TILE_WIDTH,
            TILE_WIDTH * (self.tile.resolution.y / self.tile.resolution.x)
        )

        # make tile_size one pixel smaller. without this, one pixel gaps can appear between tiles
        tile_size = mymath.multiply_compwise(tile_size, Vec2d(
            (self.tile.resolution.x - 1) / self.tile.resolution.x,
            (self.tile.resolution.y - 1) / self.tile.resolution.y
        ))

        corner = camera.get_bottom_left_corner_world_space()

        corner = mymath.multiply_compwise(mymath.floor_vec(mymath.divide_compwise(corner, tile_size)), tile_size)
        tile_map_size = mymath.ceil_vec(mymath.divide_compwise(camera.get_window_size(), self.tile.resolution)) + mymath.VectorInt(1, 1)

        for x in range(tile_map_size.x):
            for y in range(tile_map_size.y):
                self.tile.position = corner + mymath.multiply_compwise(Vec2d(x, y), tile_size)
                self.tile.render(camera)
