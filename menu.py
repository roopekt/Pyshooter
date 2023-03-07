import pygame
from pygame import Rect
import pygame_gui
import ipfinder
import scene
from gameparameters import GameParameters
from typing import Optional
from communication import CommunicationClient, CommunicationServer
import messages
from thread_owner import ThreadOwner
import threading
import time
import math

BACKGROUND_COLOR = pygame.Color("#0e0e0f")
GAME_START_DELAY_SECONDS = 3
GUI_THEME_PATH = "assets/default-theme.json"

def get_default_local_ip():
    try:
        return ipfinder.get_local_ip()
    except Exception as exception:
        print(exception)
        return ""

class StartMenu(scene.Scene):

    def __init__(self, window: pygame.Surface):
        super().__init__(window, max_fps=50)
        self.gui_manager = pygame_gui.UIManager(self.window.get_size(), GUI_THEME_PATH)
        self.game_parameters: Optional[GameParameters] = None

        self.local_ip_label = pygame_gui.elements.UILabel(
            text="Local ip (ipv4)",
            relative_rect=Rect(0, 50, 250, 20),
            anchors={"centerx": "centerx", "top": "top"},
            manager=self.gui_manager
        )
        self.local_ip_entry = pygame_gui.elements.UITextEntryLine(
            initial_text=get_default_local_ip(),
            placeholder_text="pleace specify",
            relative_rect=Rect(0, 0, 250, -1),
            anchors={"centerx": "centerx", "top_target": self.local_ip_label},
            manager=self.gui_manager
        )
        self.name_label = pygame_gui.elements.UILabel(
            text="Name",
            relative_rect=Rect(0, 10, 250, 20),
            anchors={"centerx": "centerx", "top_target": self.local_ip_entry},
            manager=self.gui_manager
        )
        self.name_entry = pygame_gui.elements.UITextEntryLine(
            placeholder_text="pleace specify",
            relative_rect=Rect(0, 0, 250, -1),
            anchors={"centerx": "centerx", "top_target": self.name_label},
            manager=self.gui_manager
        )
        self.host_game_button = pygame_gui.elements.UIButton(
            text="Host Game",
            relative_rect=Rect(-70, 20, 120, 30),
            anchors={"centerx": "centerx", "top_target": self.name_entry},
            manager=self.gui_manager
        )
        self.join_game_button = pygame_gui.elements.UIButton(
            text="Join Game",
            relative_rect=Rect(70, 20, 120, 30),
            anchors={"centerx": "centerx", "top_target": self.name_entry},
            manager=self.gui_manager
        )

        self.remote_server_ip_label = pygame_gui.elements.UILabel(
            text="Remote server ip (ipv4)",
            relative_rect=Rect(0, 50, 250, 20),
            anchors={"centerx": "centerx", "top_target": self.join_game_button},
            manager=self.gui_manager
        )
        self.remote_server_ip_entry = pygame_gui.elements.UITextEntryLine(
            placeholder_text="pleace specify",
            relative_rect=Rect(0, 0, 250, -1),
            anchors={"centerx": "centerx", "top_target": self.remote_server_ip_label},
            manager=self.gui_manager
        )
        self.final_join_game_button = pygame_gui.elements.UIButton(
            text="Join",
            relative_rect=Rect(0, 10, 90, 30),
            anchors={"centerx": "centerx", "top_target": self.remote_server_ip_entry},
            manager=self.gui_manager
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
                else:
                    raise Exception(f"Unknown button was pressed: {event.ui_element}")

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

class LobbyClient(scene.Scene):

    def __init__(self, communication_client: CommunicationClient, game_parameters: GameParameters, window: pygame.Surface):
        self.communication_client = communication_client
        self.game_parameters = game_parameters
        super().__init__(window, max_fps=50)
        self.gui_manager = pygame_gui.UIManager(self.window.get_size(), GUI_THEME_PATH)
        self.join_lobby_server()

        self.player_list_gui = pygame_gui.elements.UITextBox(
            html_text="loading...",
            relative_rect=Rect(0, 20, 250, 250),
            anchors={"centerx": "centerx", "top": "top"},
            object_id=pygame_gui.core.ObjectID(class_id="@centered", object_id="#player-list"),
            manager=self.gui_manager
        )
        self.start_game_button = pygame_gui.elements.UIButton(
            text="Start Game",
            tool_tip_text=f"Start the game after {GAME_START_DELAY_SECONDS} seconds.",
            relative_rect=Rect(0, 20, 200, 30),
            anchors={"centerx": "centerx", "top_target": self.player_list_gui},
            manager=self.gui_manager
        )
        self.game_start_timer = pygame_gui.elements.UILabel(
            text="?",
            relative_rect=Rect(0, 20, 100, 30),
            anchors={"centerx": "centerx", "top_target": self.player_list_gui},
            object_id=pygame_gui.core.ObjectID(class_id="@centered", object_id="#game-start-timer"),
            visible=0,
            manager=self.gui_manager
        )

    def handle_events(self, events: list[pygame.event.Event]):
        for event in events:
            if event.type == pygame_gui.UI_BUTTON_PRESSED:
                if event.ui_element == self.start_game_button:
                    self.communication_client.send_reliable(messages.GameStartRequest())
                else:
                    raise Exception(f"Unknown button was pressed: {event.ui_element}")

            self.gui_manager.process_events(event)

    def update(self):
        self.gui_manager.update(self.delta_time / 1000)
        self.handle_messages()

    def render(self):
        self.window.fill(BACKGROUND_COLOR)
        self.gui_manager.draw_ui(self.window)
        pygame.display.flip()

    def handle_messages(self):
        for message in self.communication_client.poll_messages():
            if isinstance(message, messages.LobbyStateUpdate):
                self.update_connected_players(message)
                self.update_game_start_timer(message)
                if message.time_to_game_start != None and message.time_to_game_start <= 0:
                    self.scene_to_switch_to = scene.SCENE_GAME
                    print("Entering game.")
            else:
                self.scene_to_switch_to = scene.SCENE_GAME
                print(f"Unexpected message ({type(message)}) received by lobby. Entering game.")

    def update_connected_players(self, message: messages.LobbyStateUpdate):
        self.player_list_gui.set_text(
            '<font face="verdana" color="#FFFFFF" size=1>' +
            '\n'.join(message.connected_player_names) +
            '</font>'
        )

    def update_game_start_timer(self, message: messages.LobbyStateUpdate):
        if message.time_to_game_start != None:
            self.start_game_button.visible = 0
            self.game_start_timer.visible = 1

            timer_text = str(math.ceil(message.time_to_game_start))
            self.game_start_timer.set_text(timer_text)
        
    def join_lobby_server(self):
        self.communication_client.send_reliable(messages.EnterLobbyMessage(
            player_name = self.game_parameters.player_name
        ))

class LobbyServer(ThreadOwner):

    def __init__(self, communication_server: CommunicationServer, start = False):
        self.communication_server = communication_server
        self.max_fps = 20

        self.players: dict[messages.ObjectId, str] = {}
        self.game_start_time: Optional[float] = None

        ThreadOwner.__init__(self, start_immediately=start)
        self.add_thread(threading.Thread(target=self.mainloop), "LobbyServer")

    def mainloop(self):
        clock = pygame.time.Clock()
        while self.running:
            clock.tick(self.max_fps)

            self.handle_messages()
            self.send_post_frame_messages()

    def handle_messages(self):
        for message_with_id in self.communication_server.poll_messages():
            message = message_with_id.payload
            sender_id = message_with_id.sender_id

            if isinstance(message, messages.EnterLobbyMessage):
                self.players[sender_id] = message.player_name
            elif isinstance(message, messages.GameStartRequest):
                self.game_start_time = time.time() + GAME_START_DELAY_SECONDS
            else:
                raise Exception(f"Lobby server cannot handle a {type(message)}.")
            
    def send_post_frame_messages(self):
        self.communication_server.send_to_all_reliable(messages.LobbyStateUpdate(
            connected_player_names = list(self.players.values()),
            time_to_game_start = None if self.game_start_time == None else self.game_start_time - time.time()
        ))
