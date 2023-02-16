import pygame
import pymunk
from pymunk import Vec2d
import threading
from communication import CommunicationServer
import messages
import player

MAX_FPS = 50

class GameServer:
    
    def __init__(self, communication_server: CommunicationServer, start = False):
        self.physics_world = pymunk.Space()
        self.physics_world.gravity = Vec2d(0, -9.81)
        self.server_thread = None
        self.communication_server = communication_server
        self.players: dict[str, player.ServerPlayer] = {}

        self.floor_body = pymunk.Body(body_type=pymunk.Body.STATIC)
        self.floor_collider = pymunk.Segment(self.floor_body, (-100, 0), (100, 0), radius=0)
        self.floor_collider.elasticity = 0.8
        self.physics_world.add(self.floor_body, self.floor_collider)

        if start:
            self.start()

    def mainloop(self):
        self.should_run = True
        clock = pygame.time.Clock()
        while self.should_run:
            clock.tick(MAX_FPS)
            self.handle_messages()
            self.physics_world.step(1/MAX_FPS)
            self.send_post_frame_messages()

    def handle_messages(self):
        for message_with_id in self.communication_server.poll_messages():
            message = message_with_id.payload
            sender_id = message_with_id.sender_id

            if sender_id not in self.players:
                self.players[sender_id] = player.ServerPlayer(sender_id, self.physics_world)

            if isinstance(message, messages.MousePositionUpdate):
                self.players[sender_id].mouse_position_world_space = message.mouse_position_world_space
            else:
                raise Exception(f"Server cannot handle a {type(message)}.")

    def send_post_frame_messages(self):
        for player in self.players.values():
            self.communication_server.send_to_all(player.get_position_update_message())

    def start(self):
        assert(self.server_thread == None)
        self.server_thread = threading.Thread(target=self.mainloop)
        self.server_thread.start()

    def stop(self):
        if self.server_thread != None:
            self.should_run = False
            self.server_thread.join()
            self.server_thread = None

