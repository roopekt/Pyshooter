from abc import ABC, abstractmethod
import pygame
from typing import Optional, NewType, Sequence
import datetime
import random
import pathlib
from os import makedirs
from fpscalculator import FPSCalculator
from windowcontainer import WindowContainer

SceneType = NewType("SceneType", str)
SCENE_QUIT = SceneType("quit")
SCENE_STARTMENU = SceneType("startmenu")
SCENE_LOBBY = SceneType("lobby")
SCENE_GAME = SceneType("game")

class Scene(ABC):

    def __init__(self, window_container: WindowContainer, max_fps: float):
        self.window_container = window_container
        self.max_fps = max_fps
        self.delta_time = 1 / max_fps
        self.scene_to_switch_to: Optional[SceneType] = None
        self.FPS_calculator = FPSCalculator()

        self.default_resolution = self.window_container.window.get_size()
        self.fullscreen_active = False

    def mainloop(self):
        clock = pygame.time.Clock()
        while self.scene_to_switch_to == None:
            self.delta_time = clock.tick(round(self.max_fps)) / 1000

            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT:
                    self.scene_to_switch_to = SCENE_QUIT
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_F2:
                    self.save_screenshot()
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                    self.fullscreen_active = not self.fullscreen_active
                    self.window_container.set_fullscreen(self.fullscreen_active)

            self.handle_events(events)
            self.update()
            self.render()
            fps = self.FPS_calculator.get_FPS_str(self.delta_time)
            pygame.display.set_caption(f"Pyshooter {fps} FPS")
                    
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
        pygame.image.save(self.window_container.window, save_path)
        print(f'Screenshot saved to "{save_path}"')
