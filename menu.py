import pygame
from pygame import Rect
import pygame_gui
import scene
import gameparameters
from typing import Optional
from communication import CommunicationClient, CommunicationServer
import messages
from thread_owner import ThreadOwner
import threading
import time
import math
import connectioncode
import errors
from windowcontainer import WindowContainer
from game import playercolor

BACKGROUND_COLOR = pygame.Color("#0e0e0f")
GAME_START_DELAY_SECONDS = 3
GUI_THEME_PATH = "assets/default-theme.json"

def get_default_local_ip():
    try:
        return gameparameters.get_local_ip()
    except Exception as exception:
        print(exception)
        return ""

def get_default_external_ip():
    try:
        return gameparameters.get_external_ip()
    except Exception as exception:
        print(exception)
        return ""

# UITextEntryBox that ignores all input
class SelectableTextBox(pygame_gui.elements.UITextEntryBox):

    def process_event(self, event: pygame.event.Event) -> bool:
        is_copy_command = (event.type == pygame.KEYDOWN and
            event.key == pygame.K_c and
            (event.mod & pygame.KMOD_CTRL, event.mod & pygame.KMOD_META) != (0, 0)
        )
        other_allowed_keys = (pygame.K_HOME, pygame.K_END, pygame.K_RIGHT, pygame.K_UP, pygame.K_LEFT, pygame.K_DOWN)

        if event.type == pygame.KEYDOWN and not is_copy_command and not event.key in other_allowed_keys:
            return False
        else:
            return super().process_event(event)

class StartMenu(scene.Scene):

    def __init__(self, window_container: WindowContainer):
        super().__init__(window_container, max_fps=50)
        self.gui_manager = pygame_gui.UIManager(self.window_container.window.get_size(), GUI_THEME_PATH)
        self.game_parameters: Optional[gameparameters.GameParameters] = None

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
        self.external_ip_label = pygame_gui.elements.UILabel(
            text="External ip (ipv4)",
            relative_rect=Rect(0, 10, 250, 20),
            anchors={"centerx": "centerx", "top_target": self.local_ip_entry},
            manager=self.gui_manager
        )
        self.external_ip_entry = pygame_gui.elements.UITextEntryLine(
            initial_text=get_default_external_ip(),
            placeholder_text="pleace specify",
            relative_rect=Rect(0, 0, 250, -1),
            anchors={"centerx": "centerx", "top_target": self.external_ip_label},
            manager=self.gui_manager
        )
        self.name_label = pygame_gui.elements.UILabel(
            text="Name",
            relative_rect=Rect(0, 10, 250, 20),
            anchors={"centerx": "centerx", "top_target": self.external_ip_entry},
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

        self.select_server_type_label = pygame_gui.elements.UILabel(
            text="Select server type",
            relative_rect=Rect(0, 50, 250, 20),
            anchors={"centerx": "centerx", "top_target": self.join_game_button},
            manager=self.gui_manager
        )
        self.LAN_host_button = pygame_gui.elements.UIButton(
            text="LAN",
            tool_tip_text="Everyone must be on the same network. More reliable.",
            relative_rect=Rect(-70, 0, 120, 30),
            anchors={"centerx": "centerx", "top_target": self.select_server_type_label},
            manager=self.gui_manager
        )
        self.public_host_button = pygame_gui.elements.UIButton(
            text="Public",
            tool_tip_text="Works from anywhere. Less reliable, uses UPnP.",
            relative_rect=Rect(70, 0, 120, 30),
            anchors={"centerx": "centerx", "top_target": self.select_server_type_label},
            manager=self.gui_manager
        )
        self.set_host_panel_visibility(False)

        self.connection_code_label = pygame_gui.elements.UILabel(
            text="Connection code",
            relative_rect=Rect(0, 50, 250, 20),
            anchors={"centerx": "centerx", "top_target": self.join_game_button},
            manager=self.gui_manager
        )
        self.connection_code_entry = pygame_gui.elements.UITextEntryLine(
            placeholder_text="pleace specify",
            relative_rect=Rect(0, 0, 250, -1),
            anchors={"centerx": "centerx", "top_target": self.connection_code_label},
            manager=self.gui_manager
        )
        self.final_join_game_button = pygame_gui.elements.UIButton(
            text="Join",
            relative_rect=Rect(0, 10, 90, 30),
            anchors={"centerx": "centerx", "top_target": self.connection_code_entry},
            manager=self.gui_manager
        )
        self.set_join_panel_visibility(False)

    def handle_events(self, events: list[pygame.event.Event]):
        for event in events:
            if event.type == pygame_gui.UI_BUTTON_PRESSED:
                if event.ui_element == self.host_game_button:
                    self.set_host_panel_visibility(True)
                    self.set_join_panel_visibility(False)
                elif event.ui_element == self.join_game_button:
                    self.set_host_panel_visibility(False)
                    self.set_join_panel_visibility(True)
                
                elif event.ui_element == self.LAN_host_button:
                    self.try_enter_lobby(is_host=True,  is_public_host=False)
                elif event.ui_element == self.public_host_button:
                    self.try_enter_lobby(is_host=True,  is_public_host=True )
                elif event.ui_element == self.final_join_game_button:
                    self.try_enter_lobby(is_host=False, is_public_host=False)

            elif event.type == pygame.VIDEORESIZE:
                self.gui_manager.set_window_resolution(self.window_container.window.get_size())

            self.gui_manager.process_events(event)

    def update(self):
        self.gui_manager.update(self.delta_time)

    def render(self):
        self.window_container.window.fill(BACKGROUND_COLOR)
        self.gui_manager.draw_ui(self.window_container.window)
        pygame.display.flip()

    def set_host_panel_visibility(self, visible: bool):
        visibility = 1 if visible else 0
        self.select_server_type_label.visible = visibility
        self.LAN_host_button.visible = visibility
        self.public_host_button.visible = visibility

    def set_join_panel_visibility(self, visible: bool):
        visibility = 1 if visible else 0
        self.connection_code_label.visible = visibility
        self.connection_code_entry.visible = visibility
        self.final_join_game_button.visible = visibility

    def try_enter_lobby(self, is_host: bool, is_public_host: bool):
        remote_ip = None
        if not is_host:
            connection_code = self.connection_code_entry.get_text()
            try:
                remote_ip = connectioncode.decode_connection_code(connection_code)
            except Exception as exception:
                error_window = pygame_gui.windows.UIMessageWindow(
                    window_title="Invalid connection code",
                    html_message=str(exception),
                    rect=Rect(50, 50, 300, 200),
                    manager=self.gui_manager
                )

                errors.log_nonfatal(exception)
                return

        self.game_parameters = gameparameters.GameParameters(
            is_host = is_host,
            is_public_host = is_public_host,
            own_local_ip = self.local_ip_entry.get_text(),
            own_external_ip = self.external_ip_entry.get_text(),
            remote_server_ip = remote_ip,
            player_name = self.name_entry.get_text()
        )

        self.scene_to_switch_to = scene.SCENE_LOBBY

class LobbyClient(scene.Scene):

    def __init__(self, communication_client: CommunicationClient, game_parameters: gameparameters.GameParameters, window_container: WindowContainer):
        self.communication_client = communication_client
        self.communication_client.remove_messages_of_other_types(messages.LobbyMessage)
        self.game_parameters = game_parameters
        super().__init__(window_container, max_fps=50)
        self.gui_manager = pygame_gui.UIManager(self.window_container.window.get_size(), GUI_THEME_PATH)
        self.connection_code = connectioncode.encode_ip_address(game_parameters.get_server_ip())
        self.join_lobby_server()

        self.connection_code_label = pygame_gui.elements.UILabel(
            text="Connection code",
            relative_rect=Rect(0, 20, 250, 30),
            anchors={"centerx": "centerx", "top": "top"},
            manager=self.gui_manager
        )
        self.connection_code_textbox = SelectableTextBox(
            initial_text=self.connection_code,
            relative_rect=Rect(0, 0, 250, 40),
            anchors={"centerx": "centerx", "top_target": self.connection_code_label},
            object_id=pygame_gui.core.ObjectID(class_id="@centered", object_id="#connection-code-textbox"),
            manager=self.gui_manager
        )
        self.player_list_label = pygame_gui.elements.UILabel(
            text="Connected players",
            relative_rect=Rect(0, 20, 250, 30),
            anchors={"centerx": "centerx", "top_target": self.connection_code_textbox},
            manager=self.gui_manager
        )
        self.player_list_textbox = pygame_gui.elements.UITextBox(
            html_text="loading...",
            relative_rect=Rect(0, 0, 250, 250),
            anchors={"centerx": "centerx", "top_target": self.player_list_label},
            object_id=pygame_gui.core.ObjectID(class_id="@centered", object_id="#player-list"),
            manager=self.gui_manager
        )
        self.start_game_button = pygame_gui.elements.UIButton(
            text="Start Game",
            tool_tip_text=f"Start the game after {GAME_START_DELAY_SECONDS} seconds.",
            relative_rect=Rect(0, 20, 200, 30),
            anchors={"centerx": "centerx", "top_target": self.player_list_textbox},
            manager=self.gui_manager
        )
        self.game_start_timer = pygame_gui.elements.UILabel(
            text="?",
            relative_rect=Rect(0, 20, 100, 30),
            anchors={"centerx": "centerx", "top_target": self.player_list_textbox},
            object_id=pygame_gui.core.ObjectID(class_id="@centered", object_id="#game-start-timer"),
            visible=0,
            manager=self.gui_manager
        )

    def handle_events(self, events: list[pygame.event.Event]):
        for event in events:
            if event.type == pygame_gui.UI_BUTTON_PRESSED:
                if event.ui_element == self.start_game_button:
                    self.communication_client.send_reliable(messages.GameStartRequest())
            elif event.type == pygame.VIDEORESIZE:
                self.gui_manager.set_window_resolution(self.window_container.window.get_size())

            self.gui_manager.process_events(event)

    def update(self):
        self.gui_manager.update(self.delta_time)
        self.handle_messages()

    def render(self):
        self.window_container.window.fill(BACKGROUND_COLOR)
        self.gui_manager.draw_ui(self.window_container.window)
        pygame.display.flip()

    def handle_messages(self):
        for message in self.communication_client.poll_messages(type_to_poll=messages.LobbyMessage):
            if isinstance(message, messages.LobbyStateUpdate):
                self.update_connected_players(message)
                self.update_game_start_timer(message)
                if message.time_to_game_start != None and message.time_to_game_start <= 0:
                    self.scene_to_switch_to = scene.SCENE_GAME
                    print("Entering game.")
            else:
                raise Exception(f"LobbyClient can't handle a {type(message)}")

    def update_connected_players(self, message: messages.LobbyStateUpdate):
        text = '\n'.join([
            f"<font color='{playercolor.get_pygame_gui_color(name)}'>{name}</font>"
            for name in message.connected_player_names
        ])#color={playercolor.get_pygame_gui_color(name)}
        self.player_list_textbox.set_text(text)

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
        self.communication_server.remove_messages_of_other_types(messages.LobbyMessage)
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
        for message_with_id in self.communication_server.poll_messages(type_to_poll=messages.LobbyMessage):
            message = message_with_id.payload
            sender_id = message_with_id.sender_id

            if isinstance(message, messages.EnterLobbyMessage):
                self.players[sender_id] = message.player_name
            elif isinstance(message, messages.GameStartRequest):
                self.game_start_time = time.time() + GAME_START_DELAY_SECONDS
            else:
                raise Exception(f"LobbyServer can't handle a {type(message)}")
            
    def send_post_frame_messages(self):
        self.communication_server.send_to_all_reliable(messages.LobbyStateUpdate(
            connected_player_names = list(self.players.values()),
            time_to_game_start = None if self.game_start_time == None else self.game_start_time - time.time()
        ))
