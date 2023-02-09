import pygame
import pymunk
import threading
from time import time
from math import sin
from communication import CommunicationServer
import messages

MAX_FPS = 50

class GameServer:
    
    def __init__(self, communication_server: CommunicationServer, start = False):
        self.physics_world = pymunk.Space()
        self.server_thread = None
        self.communication_server = communication_server

        self.temp = 0

        if start:
            self.start()

    def mainloop(self):
        self.should_run = True
        clock = pygame.time.Clock()
        while self.should_run:
            clock.tick(MAX_FPS)

            self.handle_messages()

            self.communication_server.send_to_all(
                messages.TempMessage(sin(time()) + self.temp)
            )

    def handle_messages(self):
        for message in self.communication_server.poll_messages():
            if isinstance(message, messages.TempReliableToServer):
                print("update")
                self.temp = message.new_value
            else:
                raise Exception(f"Server cannot handle a {type(message)}.")

    def start(self):
        assert(self.server_thread == None)
        self.server_thread = threading.Thread(target=self.mainloop)
        self.server_thread.start()

    def stop(self):
        if self.server_thread != None:
            self.should_run = False
            self.server_thread.join()
            self.server_thread = None

