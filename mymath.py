import pymunk
import pygame

def tuple_to_pymunk_vec(tuple: tuple[float, float]):
    return pymunk.Vec2d(tuple[0], tuple[1])

def pymunk_vec_to_pygame_vec(pymunk_vec: pymunk.Vec2d):
    return pygame.Vector2(pymunk_vec.x, pymunk_vec.y)

def pygame_vec_to_pymunk_vec(pygame_vec: pygame.Vector2):
    return pymunk.Vec2d(pygame_vec.x, pygame_vec.y)