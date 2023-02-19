from dataclasses import dataclass, field
import pygame
from pymunk import Vec2d
import mymath

@dataclass
class Camera:
    window: pygame.surface.Surface
    position: Vec2d = field(default_factory=Vec2d.zero)
    height: float = 25

    # scale factor to convert between world units and pixels
    def get_graphical_scale_factor(self):
        return self.window.get_height() / self.height

    def get_screen_position(self, world_position: Vec2d):
        p = world_position - self.position
        p = Vec2d(p.x, -p.y)
        p *= self.get_graphical_scale_factor()
        p += self.get_window_size() / 2
        return pygame.Vector2(p.x, p.y)

    def get_world_position(self, screen_position: tuple[float, float]):
        p = mymath.tuple_to_pymunk_vec(screen_position)
        p -= self.get_window_size() / 2
        p /= self.get_graphical_scale_factor()
        p = Vec2d(p.x, -p.y)
        p += self.position
        return p
    
    def get_bottom_left_corner_world_space(self):
        return self.get_world_position((0, self.window.get_height() - 1))
    
    def get_window_size(self):
        return mymath.tuple_to_pymunk_vec(self.window.get_size())