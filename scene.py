from abc import ABC, abstractmethod
import pygame
from typing import Optional, NewType
import datetime
import random
import pathlib
from os import makedirs

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
            self.delta_time = clock.tick(round(self.max_fps))

            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT:
                    self.scene_to_switch_to = SCENE_QUIT
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_F2:
                    self.save_screenshot()

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

    def save_screenshot(self):
        file_name = f"{datetime.datetime.now().strftime('%d-%m-%Y_%H-%M-%S')}_{random.randrange(10**10, 10**11)}.png"
        save_folder = pathlib.Path.home() / "Pictures" / "Screenshots" / "Pyshooter"
        save_path = save_folder / file_name

        makedirs(save_folder, exist_ok=True)
        pygame.image.save(self.window, save_path)
        print(f'Screenshot saved to "{save_path}"')
