import pygame
from pygame import Color, Vector2
from communication import CommunicationClient
import messages
from random import random

MAX_FPS = 60

class GameClient:

    def __init__(self, communication_client: CommunicationClient):
        self.temp_value = 0
        self.communication_client = communication_client

    def mainloop(self):
        pygame.init()

        self.should_run = True
        clock = pygame.time.Clock()
        self.window = pygame.display.set_mode((640, 480), pygame.RESIZABLE)

        while self.should_run:
            clock.tick(MAX_FPS)

            self.handle_events()
            self.handle_messages()
        
            self.window.fill((0, 0, 0))
            pygame.draw.circle(self.window, Color(255,0,0), Vector2(100, 150+50*self.temp_value), 10)
            pygame.display.flip()

        pygame.quit()

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.should_run = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                self.communication_client.send(messages.TempReliableToServer(random()))

    def handle_messages(self):
        for message in self.communication_client.poll_messages():
            if isinstance(message, messages.TempMessage):
                self.temp_value = message.value
            else:
                raise Exception(f"Client cannot handle a {type(message)}.")
