import pygame
import pymunk
from pymunk import Vec2d
from threading import Thread
from thread_owner import ThreadOwner
from communication import CommunicationServer
import messages
from . import player, bullet

MAX_TPS = 50

class GameServer(ThreadOwner):
    
    def __init__(self, communication_server: CommunicationServer, start = False):
        self.physics_world = pymunk.Space()
        self.physics_world.gravity = Vec2d(0, -9.81)
        self.communication_server = communication_server
        self.players: dict[messages.ObjectId, player.ServerPlayer] = {}
        self.bullets: list[bullet.ServerBullet] = []

        self.floor_body = pymunk.Body(body_type=pymunk.Body.STATIC)
        self.floor_collider = pymunk.Segment(self.floor_body, (-100, 0), (100, 0), radius=0)
        self.floor_collider.elasticity = 0.8
        self.physics_world.add(self.floor_body, self.floor_collider)

        ThreadOwner.__init__(self, start_immediately=start)
        self.add_thread(Thread(target=self.mainloop), "GameServer")

    def mainloop(self):
        self.should_run = True
        clock = pygame.time.Clock()
        while self.should_run:
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
                self.players[sender_id] = player.ServerPlayer(sender_id, self.physics_world)

            if isinstance(message, messages.MousePositionUpdate):
                self.players[sender_id].mouse_position_world_space = message.mouse_position_world_space
            elif isinstance(message, messages.ShootMessage):
                self.bullets.append(bullet.ServerBullet(message, sender_id))
                self.players[sender_id].apply_recoil(message)
            else:
                raise Exception(f"Server cannot handle a {type(message)}.")

    def update_bullets(self, delta_time: float):
        bullets_to_destroy = []
        for bullet in self.bullets:
            bullet.update_position(delta_time)

            if bullet.should_be_destroyed():
                bullets_to_destroy.append(bullet)
                self.communication_server.send_to_all_reliable(messages.BulletDestroyMessage(bullet.id))

        for bullet in bullets_to_destroy:
            self.bullets.remove(bullet)

    def send_post_frame_messages(self):
        for player in self.players.values():
            self.communication_server.send_to_all(player.get_position_update_message())
        for bullet in self.bullets:
            self.communication_server.send_to_all(bullet.get_state_update_message())
