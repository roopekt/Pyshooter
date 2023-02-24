import pygame
from pygame import Rect
import pygame_gui
import ipfinder
import scene
from gameparameters import GameParameters
from typing import Optional

BACKGROUND_COLOR = pygame.Color("#2a2a25")

def get_default_local_ip():
    try:
        return ipfinder.get_local_ip()
    except Exception as exception:
        print(exception)
        return ""

class StartMenu(scene.Scene):

    def __init__(self, window: pygame.Surface):
        super().__init__(window, max_fps=50)
        self.gui_manager = pygame_gui.UIManager(self.window.get_size())
        self.game_parameters: Optional[GameParameters] = None

        self.local_ip_label = pygame_gui.elements.UILabel(
            text="Local ip (ipv4)",
            relative_rect=Rect(0, 50, 250, 20),
            anchors={"centerx": "centerx", "top": "top"}
        )
        self.local_ip_entry = pygame_gui.elements.UITextEntryLine(
            initial_text=get_default_local_ip(),
            placeholder_text="pleace specify",
            relative_rect=Rect(0, 0, 250, -1),
            anchors={"centerx": "centerx", "top_target": self.local_ip_label}
        )
        self.name_label = pygame_gui.elements.UILabel(
            text="Name",
            relative_rect=Rect(0, 10, 250, 20),
            anchors={"centerx": "centerx", "top_target": self.local_ip_entry}
        )
        self.name_entry = pygame_gui.elements.UITextEntryLine(
            placeholder_text="pleace specify",
            relative_rect=Rect(0, 0, 250, -1),
            anchors={"centerx": "centerx", "top_target": self.name_label}
        )
        self.host_game_button = pygame_gui.elements.UIButton(
            text="Host Game",
            relative_rect=Rect(-70, 20, 120, 30),
            anchors={"centerx": "centerx", "top_target": self.name_entry}
        )
        self.join_game_button = pygame_gui.elements.UIButton(
            text="Join Game",
            relative_rect=Rect(70, 20, 120, 30),
            anchors={"centerx": "centerx", "top_target": self.name_entry}
        )

        self.remote_server_ip_label = pygame_gui.elements.UILabel(
            text="Remote server ip (ipv4)",
            relative_rect=Rect(0, 50, 250, 20),
            anchors={"centerx": "centerx", "top_target": self.join_game_button}
        )
        self.remote_server_ip_entry = pygame_gui.elements.UITextEntryLine(
            placeholder_text="pleace specify",
            relative_rect=Rect(0, 0, 250, -1),
            anchors={"centerx": "centerx", "top_target": self.remote_server_ip_label}
        )
        self.final_join_game_button = pygame_gui.elements.UIButton(
            text="Join",
            relative_rect=Rect(0, 10, 90, 30),
            anchors={"centerx": "centerx", "top_target": self.remote_server_ip_entry}
        )
        self.set_join_panel_visibility(False)

    def handle_events(self, events: list[pygame.event.Event]):
        for event in events:
            if event.type == pygame_gui.UI_BUTTON_PRESSED:
                if event.ui_element == self.host_game_button:
                    self.update_game_parameters(is_host=True)
                    self.scene_to_switch_to = scene.SCENE_LOBBY
                elif event.ui_element == self.join_game_button:
                    self.set_join_panel_visibility(True)
                elif event.ui_element == self.final_join_game_button:
                    self.update_game_parameters(is_host=False)
                    self.scene_to_switch_to = scene.SCENE_LOBBY

            self.gui_manager.process_events(event)

    def update(self):
        self.gui_manager.update(self.delta_time / 1000)

    def render(self):
        self.window.fill(BACKGROUND_COLOR)
        self.gui_manager.draw_ui(self.window)
        pygame.display.flip()

    def set_join_panel_visibility(self, visible: bool):
        visibility = 1 if visible else 0
        self.remote_server_ip_label.visible = visibility
        self.remote_server_ip_entry.visible = visibility
        self.final_join_game_button.visible = visibility

    def update_game_parameters(self, is_host: bool):
        self.game_parameters = GameParameters(
            is_host=is_host,
            local_ip=self.local_ip_entry.get_text(),
            remote_server_ip=self.remote_server_ip_entry.get_text(),
            player_name=self.name_entry.get_text()
        )

class Lobby(scene.Scene):

    def __init__(self, window: pygame.Surface):
        super().__init__(window, max_fps=50)
        self.gui_manager = pygame_gui.UIManager(self.window.get_size())

    def handle_events(self, events: list[pygame.event.Event]):
        for event in events:
            if event.type == pygame_gui.UI_BUTTON_PRESSED:
                pass

            self.gui_manager.process_events(event)

    def update(self):
        self.gui_manager.update(self.delta_time / 1000)
        self.scene_to_switch_to = scene.SCENE_GAME

    def render(self):
        self.window.fill(BACKGROUND_COLOR)
        self.gui_manager.draw_ui(self.window)
        pygame.display.flip()
