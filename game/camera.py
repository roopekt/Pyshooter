from dataclasses import dataclass, field
import pygame
from pymunk import Vec2d, BB
import mymath
from typing import Sequence
from statistics import mean
from . import arenaprops
from functools import reduce

OWNING_PLAYER_BB_RADIUS = 10 # owning player is the avatar of the client we are running on
OTHER_PLAYERS_BB_RADIUS = 5

def get_player_bounding_box(player_pos: Vec2d, is_us: bool):
    radius = OWNING_PLAYER_BB_RADIUS if is_us else OTHER_PLAYERS_BB_RADIUS
    return BB.newForCircle(player_pos, radius)

def expand_BB_to_correct_aspect_ratio(bbox: BB, aspect_ratio: float):
    center = bbox.center()
    size = Vec2d((bbox.right - bbox.left), (bbox.top - bbox.bottom))

    correct_relative_top_right = Vec2d(size.y * aspect_ratio, size.x / aspect_ratio) / 2
    correct_top_right = center + correct_relative_top_right
    correct_bottom_left = center - correct_relative_top_right
    bbox = bbox.expand(correct_top_right)
    bbox = bbox.expand(correct_bottom_left)
    return bbox

def scale_BB_to_correct_size(bbox: BB, owning_player_pos: Vec2d, min_height: float, max_height: float):
    unfixed_height = bbox.top - bbox.bottom
    correct_height = mymath.clampf(unfixed_height, min_height, max_height)
    relative_bottom_left = Vec2d(bbox.left, bbox.bottom) - owning_player_pos
    relative_top_right = Vec2d(bbox.right, bbox.top) - owning_player_pos

    corrector = correct_height / unfixed_height
    correct_relative_bottom_left = relative_bottom_left * corrector
    correct_relative_top_right = relative_top_right * corrector

    bottom_left = correct_relative_bottom_left + owning_player_pos
    top_right = correct_relative_top_right+ owning_player_pos

    return BB(
        left=bottom_left.x,
        bottom=bottom_left.y,
        right=top_right.x,
        top=top_right.y
    )

@dataclass
class Camera:
    window: pygame.surface.Surface
    position: Vec2d = field(default_factory=Vec2d.zero)
    height: float = 25

    def update(self, owning_player_pos: Vec2d, other_players_pos: Sequence[Vec2d]):
        player_BBs = [get_player_bounding_box(owning_player_pos, is_us=True)]
        player_BBs += [get_player_bounding_box(p, is_us=False) for p in other_players_pos]
        camera_BB = reduce(BB.merge, player_BBs) # contains all of player_BBs
        camera_BB = expand_BB_to_correct_aspect_ratio(camera_BB, self.get_aspect_ratio())

        self.position = camera_BB.center()
        self.height = camera_BB.top - camera_BB.bottom

    # scale factor to convert between world units and pixels
    def get_graphical_scale_factor(self):
        return self.window.get_height() / self.height

    def get_screen_position(self, world_position: Vec2d):
        p = world_position - self.position
        p = Vec2d(p.x, -p.y)
        p *= self.get_graphical_scale_factor()
        p += self.get_window_size() / 2
        return mymath.pymunk_vec_to_pygame_vec(p)

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
    
    def get_aspect_ratio(self):
        window_size = self.get_window_size()
        return window_size.x / window_size.y