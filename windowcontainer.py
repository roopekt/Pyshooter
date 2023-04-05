import pygame

class WindowContainer:

    def __init__(self, default_resolution = (640, 480)):
        self.default_resolution = default_resolution
        self.set_fullscreen(False)

    def set_fullscreen(self, enable: bool):
        if enable:
            self.window = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        else:
            self.window = pygame.display.set_mode(self.default_resolution, pygame.RESIZABLE)
