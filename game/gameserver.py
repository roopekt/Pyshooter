import pygame
import pymunk
from pymunk import Vec2d
from threading import Thread
from thread_owner import ThreadOwner
from communication import CommunicationServer
import messages
from .player import ServerPlayer
from .bullet import ServerBullet
from .floor import ServerFloor
from itertools import permutations

MAX_TPS = 50

class GameServer(ThreadOwner):
    
    def __init__(self, communication_server: CommunicationServer, start = False):
        self.physics_world = pymunk.Space()
        self.physics_world.gravity = Vec2d(0, -9.81)
        self.physics_world.add_default_collision_handler().pre_solve = self.on_collision

        self.communication_server = communication_server
        self.players: dict[messages.ObjectId, ServerPlayer] = {}
        self.bullets: dict[messages.ObjectId, ServerBullet] = {}
        self.floor = ServerFloor(self.physics_world)

        ThreadOwner.__init__(self, start_immediately=start)
        self.add_thread(Thread(target=self.mainloop), "GameServer")

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
        for message_with_id in self.communication_server.poll_messages():
            message = message_with_id.payload
            sender_id = message_with_id.sender_id

            if sender_id not in self.players:
                self.players[sender_id] = ServerPlayer(sender_id, self.physics_world)

            if isinstance(message, messages.MousePositionUpdate):
                self.players[sender_id].mouse_position_world_space = message.mouse_position_world_space
            elif isinstance(message, messages.ShootMessage):
                new_bullet = ServerBullet(message, sender_id, self.physics_world)
                self.bullets[new_bullet.id] = new_bullet
                self.players[sender_id].apply_recoil(message)
            else:
                raise Exception(f"Server cannot handle a {type(message)}.")

    def update_bullets(self, delta_time: float):
        bullet_ids_to_destroy = []
        for bullet in self.bullets.values():
            bullet.update_position(delta_time)

            if bullet.should_be_destroyed():
                bullet_ids_to_destroy.append(bullet.id)

        for bullet_id in bullet_ids_to_destroy:
            self.destroy_bullet(bullet_id)

    def destroy_bullet(self, bullet_id: messages.ObjectId):
        bullet = self.bullets[bullet_id]
        self.physics_world.remove(bullet.physics_body, bullet.collider)
        self.bullets.pop(bullet_id)
        self.communication_server.send_to_all_reliable(messages.BulletDestroyMessage(bullet_id))

    def send_post_frame_messages(self):
        for player in self.players.values():
            self.communication_server.send_to_all(player.get_position_update_message())
        for bullet in self.bullets.values():
            self.communication_server.send_to_all(bullet.get_state_update_message())

    def on_collision(self, arbiter, space, data):
        for colliderA, colliderB in permutations(arbiter.shapes):
            if colliderA.type == ServerBullet:
                bulletA = self.bullets[colliderA.object_id]

                if colliderB.type == ServerBullet:
                    self.destroy_bullet(bulletA.id)
                    self.destroy_bullet(colliderB.object_id)
                    return True
                elif colliderB.type == ServerPlayer and colliderB.object_id != bulletA.shooter_id:
                    self.players[colliderB.object_id].health -= bulletA.damage
                    self.destroy_bullet(bulletA.id)
                    return True

        return True
