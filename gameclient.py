import pygame
from pygame import Color, Vector2

MAX_FPS = 60

class GameClient:

    def __init__(self, temp_server):
        self.temp_value = 0
        self.temp_server = temp_server

    def mainloop(self):
        pygame.init()

        self.should_run = True
        clock = pygame.time.Clock()
        self.window = pygame.display.set_mode((640, 480), pygame.RESIZABLE)

        while self.should_run:
            clock.tick(MAX_FPS)

            self.handle_events()
            self.temp_value = self.temp_server.temp_value
        
            self.window.fill((0, 0, 0))
            pygame.draw.circle(self.window, Color(255,0,0), Vector2(100, 100+50*self.temp_value), 10)
            pygame.display.flip()

        pygame.quit()

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.should_run = False
