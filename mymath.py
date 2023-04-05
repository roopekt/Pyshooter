import pymunk
import pygame
from math import floor, ceil
from dataclasses import dataclass

@dataclass
class VectorInt:
    x: int
    y: int

    def __add__(self, other):
        return VectorInt(self.x + other.x, self.y + other.y)
    
def tuple_to_pymunk_vec(tuple: tuple[float, float]):
    return pymunk.Vec2d(tuple[0], tuple[1])

def pymunk_vec_to_pygame_vec(pymunk_vec: pymunk.Vec2d):
    return pygame.Vector2(pymunk_vec.x, pymunk_vec.y)

def pygame_vec_to_pymunk_vec(pygame_vec: pygame.Vector2):
    return pymunk.Vec2d(pygame_vec.x, pygame_vec.y)

def int_vec_to_pygame_vec(int_vec: VectorInt):
    return pygame.Vector2(int_vec.x, int_vec.y)

def floor_vec(vector: pymunk.Vec2d):
    return VectorInt(floor(vector.x), floor(vector.y))

def ceil_vec(vector: pymunk.Vec2d):
    return VectorInt(ceil(vector.x), ceil(vector.y))

def multiply_compwise(a, b):
    return pymunk.Vec2d(a.x * b.x, a.y * b.y)

def divide_compwise(a, b):
    return pymunk.Vec2d(a.x / b.x, a.y / b.y)

def lerpf(a: float, b: float, t: float):
    return a + (b - a) * t

def clampf(x, _min, _max):
    return max(_min, min(_max, x))
