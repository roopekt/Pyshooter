import pygame
import pymunk
import threading
from time import time
from math import sin

MAX_FPS = 50

class GameServer:
    
    def __init__(self):
        self.physics_world = pymunk.Space()
        self.server_thread = None

        self.temp_value = 0

    def mainloop(self):
        self.should_run = True
        clock = pygame.time.Clock()
        while self.should_run:
            clock.tick(MAX_FPS)

            self.temp_value = sin(time())

    def start(self):
        assert(self.server_thread == None)
        self.server_thread = threading.Thread(target=self.mainloop)
        self.server_thread.start()

    def stop(self):
        if self.server_thread != None:
            self.should_run = False
            self.server_thread.join()
            self.server_thread = None

