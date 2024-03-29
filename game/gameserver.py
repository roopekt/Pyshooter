import pygame
import pymunk
from pymunk import Vec2d
from threading import Thread
from thread_owner import ThreadOwner
from communication import CommunicationServer
import messages
from .player import ServerPlayer
from .bullet import ServerBullet, HEAL_PROPORTION
from itertools import permutations
from . import arena
from objectid import ObjectId

MAX_TPS = 50

class GameServer(ThreadOwner):
    
    def __init__(self, communication_server: CommunicationServer, start = False):
        self.physics_world = pymunk.Space()
        self.physics_world.gravity = Vec2d(0, -9.81)
        self.physics_world.add_default_collision_handler().pre_solve = self.on_collision

        self.communication_server = communication_server
        self.communication_server.remove_messages_of_other_types(messages.GameMessage)
        self.arena = arena.ServerArena(self.physics_world)
        self.players: dict[messages.ObjectId, ServerPlayer] = {}
        self.bullets: dict[messages.ObjectId, ServerBullet] = {}

        ThreadOwner.__init__(self, start_immediately=start)
        self.add_thread(Thread(target=self.mainloop), "game-server")

    def mainloop(self):
        clock = pygame.time.Clock()
        while self.running:
            clock.tick(MAX_TPS)
            delta_time = 1/MAX_TPS

            self.handle_messages()
            self.physics_world.step(delta_time)
            self.update_bullets(delta_time)
            self.send_post_frame_messages()

    def handle_messages(self):
        for message_with_id in self.communication_server.poll_messages(type_to_poll=messages.GameMessage):
            message = message_with_id.payload
            sender_id = message_with_id.sender_id

            if sender_id not in self.players:
                self.add_player(sender_id)

            if isinstance(message, messages.MousePositionUpdate):
                self.players[sender_id].mouse_position_world_space = message.mouse_position_world_space
            elif isinstance(message, messages.ShootMessage):
                new_bullet = ServerBullet(message, sender_id, self.physics_world)
                self.bullets[new_bullet.id] = new_bullet
                self.players[sender_id].apply_recoil(message)
            elif isinstance(message, messages.JoinGameMessage):
                self.players[sender_id].name = message.player_name
                self.communication_server.send_to_all_reliable(messages.NewPlayerNotification(
                    player_id = sender_id,
                    player_name = message.player_name
                ))
            elif isinstance(message, messages.GoToLobbyRequest):
                self.communication_server.send_to_all_reliable(messages.GoToLobbyNotification())
            else:
                raise Exception(f"Server cannot handle a {type(message)}.")
            
    def add_player(self, player_id: ObjectId):
        self.players[player_id] = ServerPlayer(player_id, self.physics_world)

        # send the arena
        self.communication_server.send_reliable_to(
            self.arena.try_get_arena_update_message(update_dirty_only=False),
            player_id
        )
        # send player names
        for _player_id, _player in self.players.items():
            if _player.name != "":
                self.communication_server.send_reliable_to(
                    messages.NewPlayerNotification(_player_id, _player.name),
                    player_id
                )

    def update_bullets(self, delta_time: float):
        bullet_ids_to_destroy = []
        for bullet in self.bullets.values():
            bullet.update_position(delta_time)

            if bullet.should_be_destroyed():
                bullet_ids_to_destroy.append(bullet.id)

        for bullet_id in bullet_ids_to_destroy:
            self.destroy_bullet(bullet_id)

    def destroy_bullet(self, bullet_id: messages.ObjectId):
        if bullet_id not in self.bullets:
            return False

        bullet = self.bullets[bullet_id]
        self.physics_world.remove(bullet.physics_body, bullet.collider)
        self.bullets.pop(bullet_id)
        self.communication_server.send_to_all_reliable(messages.BulletDestroyMessage(bullet_id))
        return True

    def send_post_frame_messages(self):
        for player in self.players.values():
            self.communication_server.send_to_all(player.get_position_update_message())
        for bullet in self.bullets.values():
            self.communication_server.send_to_all(bullet.get_state_update_message())
        
        arena_update = self.arena.try_get_arena_update_message()
        if arena_update != None:
            self.communication_server.send_to_all_reliable(arena_update)

    def on_collision(self, arbiter: pymunk.Arbiter, space: pymunk.Space, data):
        for colliderA, colliderB in permutations(arbiter.shapes):
            if colliderA.type == ServerBullet:
                if colliderA.object_id not in self.bullets:
                    return True
                bulletA = self.bullets[colliderA.object_id]

                if colliderB.type == ServerBullet:
                    self.destroy_bullet(bulletA.id)
                    self.destroy_bullet(colliderB.object_id)
                    return True
                elif colliderB.type == ServerPlayer and colliderB.object_id != bulletA.shooter_id:
                    self.on_bullet_player_collision(bulletA, colliderB.object_id)
                    return True
                elif colliderB.type == arena.ServerWall:
                    self.on_bullet_wall_collision(bulletA, colliderB.object_id, arbiter)
                    return True

        return True
    
    def on_bullet_player_collision(self, bullet: ServerBullet, hit_player_id: ObjectId):
        hit_player = None
        try:
            hit_player = self.players[hit_player_id]
            hit_player.change_health(-bullet.damage)
        except KeyError:
            print(f"Didn't find player {hit_player_id} (was hit by a bullet)")

        if hit_player == None or hit_player.health <= 0:# can't heal from a dead body
            return
        try:
            shooter_player = self.players[bullet.shooter_id]
            shooter_player.change_health(HEAL_PROPORTION * bullet.damage)
        except KeyError:
            print(f"Didn't find player {bullet.shooter_id} (trying to heal)")

        self.destroy_bullet(bullet.id)  

    def on_bullet_wall_collision(self, bullet: ServerBullet, wall_id: ObjectId, arbiter: pymunk.Arbiter):
        if bullet.id_of_last_wall_hit == wall_id:
            return
        
        bullet.id_of_last_wall_hit = wall_id

        wall = None
        try:
            wall = self.arena.walls[wall_id]
        except KeyError:
            print(f"Couldn't find wall {wall_id} (was hit by a bullet)")

        if bullet.bounces_left > 0:
            bullet.velocity -= 2 * bullet.velocity.projection(arbiter.normal)
            bullet.bounces_left -= 1
            
            if wall != None:
                wall.take_damage(bullet.damage)
        else:
            self.destroy_bullet(bullet.id)
