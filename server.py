import pygame
import pymunk
import threading

MAX_FPS = 50

class Server:
    
    def __init__(self):
        self.physics_world = pymunk.Space()
        self.server_thread = None

    def mainloop(self):
        self.should_run = True
        clock = pygame.time.Clock()
        while self.should_run:
            clock.tick(MAX_FPS)

    def start(self):
        assert(self.server_thread == None)
        self.server_thread = threading.Thread(target=self.mainloop)
        self.server_thread.start()

    def stop(self):
        if self.server_thread != None:
            self.should_run = False
            self.server_thread.join()
            self.server_thread = None
