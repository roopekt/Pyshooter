from abc import ABC, abstractmethod
import pygame
from typing import Optional, NewType

SceneType = NewType("SceneType", str)
SCENE_QUIT = SceneType("quit")
SCENE_STARTMENU = SceneType("startmenu")
SCENE_LOBBY = SceneType("lobby")
SCENE_GAME = SceneType("game")

class Scene(ABC):

    def __init__(self, window: pygame.Surface, max_fps: float):
        self.window = window
        self.max_fps = max_fps
        self.delta_time = 1 / max_fps
        self.scene_to_switch_to: Optional[SceneType] = None

    def mainloop(self):
        clock = pygame.time.Clock()
        while self.scene_to_switch_to == None:
            self.delta_time = clock.tick(self.max_fps)

            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT:
                    self.scene_to_switch_to = SCENE_QUIT

            self.handle_events(events)
            self.update()
            self.render()
                    
    @abstractmethod
    def handle_events(self, events: list[pygame.event.Event]):
        pass

    @abstractmethod
    def update(self):
        pass

    @abstractmethod
    def render(self):
        pass
