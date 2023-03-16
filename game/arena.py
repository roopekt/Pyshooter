from pymunk import Vec2d
import pymunk
from .camera import Camera
import pygame
import math
import mymath
import random
import objectid
import messages
from .arenaprops import *

class ServerWall:

    def __init__(self, position: Vec2d, dimensions: Vec2d, max_health_density: float, physics_world: pymunk.Space):
        self.position = position
        self.dimensions = dimensions

        self.max_health = max_health_density * dimensions.x * dimensions.y
        self.health = self.max_health
        self.is_dirty = True# true if changed (don't modify fields directly!) since last call to Arena.get_dirty_walls

        self.id = objectid.get_new_object_id()
        self.physics_world = physics_world
        self.body = pymunk.Body(body_type=pymunk.Body.STATIC, mass=1)
        self.collider = pymunk.Poly(self.body, self.get_vertices())
        self.collider.elasticity = 0.8
        self.collider.friction = 0.5
        self.collider.type = ServerWall
        self.collider.object_id = self.id
        physics_world.add(self.body, self.collider)

    def take_damage(self, damage: float):
        self.health -= damage
        self.is_dirty = True

        if (not self.is_alive()) and self.body != None:
            self.physics_world.remove(self.body)
            self.body = None
        if (not self.is_alive()) and self.collider != None:
            self.physics_world.remove(self.collider)
            self.collider = None

    def get_vertices(self):
        directions = (Vec2d(.5, .5), Vec2d(.5, -.5), Vec2d(-.5, .5), Vec2d(-.5, -.5))
        return [self.position + mymath.multiply_compwise(dir, self.dimensions) for dir in directions]
    
    def is_alive(self):
        return self.health > 0
    
    def get_wall_update(self):
        return messages.WallUpdate(
            position = self.position,
            dimensions = self.dimensions,
            health = self.health,
            max_health = self.max_health
        )

class ClientWall:

    def __init__(self, wall_update: messages.WallUpdate):
        self.handle_wall_update(wall_update)

    def render(self, camera: Camera):
        top_left_world_space = self.position + Vec2d(-self.dimensions.x, self.dimensions.y) / 2
        top_left_screen_space = camera.get_screen_position(top_left_world_space)
        dimensions_screen_space = mymath.pymunk_vec_to_pygame_vec(self.dimensions) * camera.get_graphical_scale_factor()
        rect = pygame.Rect(top_left_screen_space, dimensions_screen_space)

        t = self.health / self.max_health
        t = t if not math.isnan(t) else 1# to make infinite health work properly
        color = WALL_ALMOST_DEAD_COLOR.lerp(WALL_ALIVE_COLOR, t)

        # pygame.draw.rect doesn't work with transparency...
        rect_surface = pygame.Surface(rect.size, pygame.SRCALPHA)
        rect_surface.fill(color)
        camera.window.blit(rect_surface, rect)

    def handle_wall_update(self, wall_update: messages.WallUpdate):
        self.position = wall_update.position
        self.dimensions = wall_update.dimensions
        self.health = wall_update.health
        self.max_health = wall_update.max_health

    def is_alive(self):
        return self.health > 0

class ServerArena:

    def __init__(self, physics_world: pymunk.Space):
        self.walls: dict[objectid.ObjectId, ServerWall] = self.get_boundary_walls(physics_world)
        for _ in range(WALL_COUNT):
            wall = self.get_random_wall(physics_world)
            self.walls[wall.id] = wall

    def try_get_arena_update_message(self, update_dirty_only: bool = True):
        walls_to_update = self.get_dirty_walls() if update_dirty_only else self.walls.values()
        if len(walls_to_update) > 0:
            wall_updates = {wall.id: wall.get_wall_update() for wall in walls_to_update}
            return messages.ArenaUpdate(wall_updates)
        else:
            return None

    # get walls that have changed since last call. Returns all if first call
    def get_dirty_walls(self):
        dirty_walls: list[ServerWall] = []
        for wall in self.walls.values():
            if wall.is_dirty:
                dirty_walls.append(wall)
                wall.is_dirty = False

        #delete dead walls
        self.walls = {wall.id: wall for wall in self.walls.values() if wall.is_alive()}

        return dirty_walls
    
    def get_boundary_walls(self, physics_world: pymunk.Space):
        walls = [
            ServerWall(Vec2d( ARENA_RADIUS, 0), Vec2d(WALL_WIDTH, 2*ARENA_RADIUS), float('inf'), physics_world),
            ServerWall(Vec2d(-ARENA_RADIUS, 0), Vec2d(WALL_WIDTH, 2*ARENA_RADIUS), float('inf'), physics_world),
            ServerWall(Vec2d(0,  ARENA_RADIUS), Vec2d(2*ARENA_RADIUS, WALL_WIDTH), float('inf'), physics_world),
            ServerWall(Vec2d(0, -ARENA_RADIUS), Vec2d(2*ARENA_RADIUS, WALL_WIDTH), float('inf'), physics_world),
        ]
        return {wall.id: wall for wall in walls}
    
    def get_random_wall(self, physics_world: pymunk.Space):
        position = Vec2d(
            random.uniform(-ARENA_RADIUS, ARENA_RADIUS),
            random.uniform(-ARENA_RADIUS, ARENA_RADIUS)
        )
        length = random.uniform(WALL_MIN_LENGTH, WALL_MAX_LENGTH)
        dimensions = Vec2d(WALL_WIDTH, length) if random.random() < .5 else Vec2d(length, WALL_WIDTH)

        return ServerWall(position, dimensions, WALL_HEALTH_DENSITY, physics_world)
    
class ClientArena:

    def __init__(self):
        self.walls: dict[objectid.ObjectId, ClientWall] = {}

    def render(self, camera: Camera):
        for wall in self.walls.values():
            wall.render(camera)

    def handle_arena_update(self, arena_update: messages.ArenaUpdate):
        for wall_id, wall_update in arena_update.wall_updates.items():
            if wall_id in self.walls:
                self.walls[wall_id].handle_wall_update(wall_update)
            else:
                self.walls[wall_id] = ClientWall(wall_update)

        #delete dead walls
        self.walls = {id: wall for id, wall in self.walls.items() if wall.is_alive()}
