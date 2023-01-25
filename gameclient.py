import pygame

MAX_FPS = 60

class Client:

    def mainloop(self):
        pygame.init()

        self.should_run = True
        clock = pygame.time.Clock()
        self.window = pygame.display.set_mode((640, 480), pygame.RESIZABLE)

        while self.should_run:
            clock.tick(MAX_FPS)

            self.handle_events()
        
            self.window.fill((0, 0, 0))
            pygame.display.flip()

        pygame.quit()

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.should_run = False
