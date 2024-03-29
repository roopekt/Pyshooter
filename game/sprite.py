import pygame
from .camera import Camera
from pymunk import Vec2d
import mymath
import math

class Sprite:
    def __init__(self, texture_path: str, sprite_width: float, pivot: str = "center", position = None, transparent = False, screen_space = False):
        self.sprite_width = sprite_width
        self.pivot = pivot
        self.position = position if position != None else Vec2d(0, 0)
        self.screen_space = screen_space

        self.unscaled_texture = pygame.image.load(texture_path)
        if transparent:
            self.unscaled_texture = self.unscaled_texture.convert_alpha()
        else:
            self.unscaled_texture = self.unscaled_texture.convert()

        self.scaled_texture = self.unscaled_texture
        self.resolution = mymath.tuple_to_pymunk_vec(self.scaled_texture.get_size())

    def render(self, camera: Camera, position = None, orientation: float = 0.0, flip_x: bool = False, flip_y: bool = False):
        if position != None:
            self.position = position

        correct_width_in_pixels = self.sprite_width * (1 if self.screen_space else camera.get_graphical_scale_factor())
        resolution_is_incorrect = int(self.resolution.x) != int(correct_width_in_pixels)

        if resolution_is_incorrect:
            self.resolution = Vec2d(
                correct_width_in_pixels,
                correct_width_in_pixels * (self.unscaled_texture.get_height() / self.unscaled_texture.get_width())
            )
            self.scaled_texture = pygame.transform.scale(self.unscaled_texture, mymath.pymunk_vec_to_pygame_vec(self.resolution))

        transformed_texture = self.scaled_texture
        if flip_x or flip_y:
            transformed_texture = pygame.transform.flip(transformed_texture, flip_x, flip_y)
        if orientation != 0.0:
            transformed_texture = pygame.transform.rotate(transformed_texture, math.degrees(orientation))

        resolution = mymath.tuple_to_pymunk_vec(transformed_texture.get_size())
        top_left_corner_position = self.position if self.screen_space else camera.get_screen_position(self.position)
        if self.pivot == "center":
            top_left_corner_position -= resolution / 2
        elif self.pivot == "corner":
            top_left_corner_position -= Vec2d(0, resolution.y - 1)
        elif self.pivot == "tl-corner":
            pass
        else:
            raise Exception(f"Unknown pivot: {self.pivot}")

        camera.window_container.window.blit(transformed_texture, top_left_corner_position)
