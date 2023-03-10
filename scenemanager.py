from game.gameserver import GameServer
from game.gameclient import GameClient
import communication
import pygame
from typing import Optional
import scene
from gameparameters import GameParameters
import menu
from game.gameclient import GameClient
import connectioncode

class SceneManager:

    def __init__(self, window: pygame.Surface, server_port: int, client_port: int):
        self.window = window
        self.server_port = server_port
        self.client_port = client_port

        self.communication_active = False
        self.game_parameters: Optional[GameParameters] = None
        self.hosting_communication_client: Optional[communication.HostingCommunicationClient] = None
        self.internet_communication_client: Optional[communication.InternetCommunicationClient] = None
        self.communication_server: Optional[communication.CommunicationServer] = None

    def mainloop(self, start_with_parameters : Optional[GameParameters] = None):
        scene_loops = {
            scene.SCENE_STARTMENU: self.startmenu_mainloop,
            scene.SCENE_LOBBY: self.lobby_mainloop,
            scene.SCENE_GAME: self.game_mainloop
        }

        self.game_parameters = start_with_parameters
        initial_scene_type = scene.SCENE_STARTMENU if start_with_parameters == None else scene.SCENE_LOBBY

        pygame.init()
        current_loop = scene_loops[initial_scene_type]
        while True:
            print(f"Switching to scene {current_loop.__name__}.")
            next_loop_key = current_loop()

            if next_loop_key == scene.SCENE_QUIT:
                break
            else:
                assert(next_loop_key != None)
                current_loop = scene_loops[next_loop_key]
        
        pygame.quit()

    def startmenu_mainloop(self):
        self.close_communication()
        start_menu = menu.StartMenu(self.window)
        start_menu.mainloop()
        self.game_parameters = start_menu.game_parameters
        return start_menu.scene_to_switch_to
    
    def lobby_mainloop(self):
        assert(self.game_parameters != None)
        print(f"Starting lobby on {self.get_connection_code()} = {self.get_server_ip()}")

        self.start_communication()
        lobby_client = menu.LobbyClient(self.get_communication_client(), self.game_parameters, self.window)

        lobby_server = None
        if self.game_parameters.is_host:
            assert(self.communication_server != None)
            lobby_server = menu.LobbyServer(self.communication_server, start=True)

        lobby_client.mainloop()

        if lobby_server != None:
            lobby_server.stop()
        return lobby_client.scene_to_switch_to
    
    def game_mainloop(self):
        assert(self.game_parameters != None)
        print(f"Starting game on {self.get_connection_code()} = {self.get_server_ip()}")

        communication_client = self.get_communication_client()
        game_client = GameClient(communication_client, self.window)

        game_server = None
        if self.game_parameters.is_host:
            assert(self.communication_server != None)
            game_server = GameServer(self.communication_server, start=True)

        game_client.mainloop()

        if game_server != None:
            game_server.stop()
        return game_client.scene_to_switch_to

    def start_communication(self):
        assert(self.game_parameters != None)
        if not self.communication_active:
            if self.game_parameters.is_host:
                self.communication_server = communication.CommunicationServer((self.game_parameters.local_ip, self.server_port), start=True)

                self.hosting_communication_client = communication.HostingCommunicationClient(self.communication_server)
                self.communication_server.hosting_client = self.hosting_communication_client
            else:
                self.internet_communication_client = communication.InternetCommunicationClient(
                    (self.game_parameters.local_ip, self.client_port),
                    (self.game_parameters.remote_server_ip, self.server_port),
                    start=True
                )

            self.communication_active = True

    def close_communication(self):
        if self.internet_communication_client != None:
            self.internet_communication_client.stop(asyncronous=True)
        if self.communication_server != None:
            self.communication_server.stop(asyncronous=True)

        self.hosting_communication_client = None
        self.internet_communication_client = None
        self.communication_server = None

        self.game_parameters = None
        self.communication_active = False

    def get_communication_client(self):
        assert(self.game_parameters != None)
        communication_client = self.hosting_communication_client if self.game_parameters.is_host else self.internet_communication_client
        assert(communication_client != None)
        return communication_client
    
    def get_server_ip(self):
        assert(self.game_parameters != None)
        server_ip = self.game_parameters.local_ip if self.game_parameters.is_host else self.game_parameters.remote_server_ip
        assert server_ip != None
        return server_ip
    
    def get_connection_code(self):
        server_ip = self.get_server_ip()
        return connectioncode.encode_ip_address(server_ip)
