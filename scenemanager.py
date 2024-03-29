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
from windowcontainer import WindowContainer

class SceneManager:

    def __init__(self, window_container: WindowContainer, server_port: int, client_port: int):
        self.window_container = window_container
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
        initial_scene_type = scene.SCENE_STARTMENU if start_with_parameters == None else scene.SCENE_GAME

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
        
        self.close_communication()
        pygame.quit()

    def startmenu_mainloop(self):
        self.close_communication()
        start_menu = menu.StartMenu(self.window_container)
        start_menu.mainloop()
        self.game_parameters = start_menu.game_parameters
        return start_menu.scene_to_switch_to
    
    def lobby_mainloop(self):
        assert(self.game_parameters != None)
        print(f"Starting lobby on {self.get_connection_code()} = {self.get_server_ip()}")

        self.start_communication()
        lobby_client = menu.LobbyClient(self.get_communication_client(), self.game_parameters, self.window_container)

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
        self.start_communication()
        print(f"Starting game on {self.get_connection_code()} = {self.get_server_ip()}")

        communication_client = self.get_communication_client()
        game_client = GameClient(communication_client, self.window_container, self.game_parameters.player_name)

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
                external_address = (self.game_parameters.own_external_ip, self.server_port) if self.game_parameters.is_public_host else None
                self.communication_server = communication.CommunicationServer((self.game_parameters.own_local_ip, self.server_port), external_address=external_address, start=True)

                self.hosting_communication_client = communication.HostingCommunicationClient(self.communication_server)
                self.communication_server.hosting_client = self.hosting_communication_client
            else:
                self.internet_communication_client = communication.InternetCommunicationClient(
                    (self.game_parameters.own_local_ip, self.client_port),
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
        return self.game_parameters.get_server_ip()
    
    def get_connection_code(self):
        server_ip = self.get_server_ip()
        return connectioncode.encode_ip_address(server_ip)
