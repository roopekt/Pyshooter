import pygame
from communication import CommunicationClient
import messages
from . import player, bullet
from time import time
from .camera import Camera
from .background import Background
from .floor import ClientFloor
import scene

RELOAD_TIME = 1 # in seconds

class GameClient(scene.Scene):

    def __init__(self, communication_client: CommunicationClient, window: pygame.Surface):
        super().__init__(window, max_fps=60)
        self.communication_client = communication_client

        self.players = {
            self.communication_client.id : player.ClientPlayer(is_owned_by_client=True)
        }
        self.bullets: dict[messages.ObjectId, bullet.ClientBullet] = {}
        self.time_of_last_shoot = time()

        pygame.init()
        self.window = window
        self.background = Background()
        self.floor = ClientFloor()
        self.camera = Camera(self.window)

    def handle_events(self, events: list[pygame.event.Event]):
        self.get_own_avatar().mouse_position_world_space = self.camera.get_world_position(pygame.mouse.get_pos())

        for event in events:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.scene_to_switch_to = scene.SCENE_STARTMENU
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.get_own_avatar().health > 0:
                    self.shoot()

    def update(self):
        self.handle_messages()
        self.update_camera()
        self.send_post_frame_messages()

    def handle_messages(self):
        for message in self.communication_client.poll_messages():
            if isinstance(message, messages.PlayerStateUpdate):
                if message.player_id not in self.players:
                    self.players[message.player_id] = player.ClientPlayer(is_owned_by_client=False)

                self.players[message.player_id].update_state(message)
            elif isinstance(message, messages.BulletStateUpdate):
                if message.bullet_id in self.bullets:
                    self.bullets[message.bullet_id].update_state(message)
                else:
                    self.bullets[message.bullet_id] = bullet.ClientBullet(
                        position = message.position,
                        radius = message.radius
                    )
            elif isinstance(message, messages.BulletDestroyMessage):
                if message.bullet_id in self.bullets:
                    self.bullets.pop(message.bullet_id)
            elif isinstance(message, messages.LobbyStateUpdate):
                print(f"{type(message)} ignored by game client.")
            else:
                raise Exception(f"Client cannot handle a {type(message)}.")

    def update_camera(self):
        self.camera.position = self.get_own_avatar().position

    def send_post_frame_messages(self):
        self.communication_client.send(messages.MousePositionUpdate(self.get_own_avatar().mouse_position_world_space))

    def render(self):
        self.background.render(self.camera)
        self.floor.render(self.camera)

        for _player in self.players.values():
            _player.render(self.camera)
        for _bullet in self.bullets.values():
            _bullet.render(self.camera)

        pygame.display.flip()

    def shoot(self):
        time_of_shoot = time()
        elapsed = time_of_shoot - self.time_of_last_shoot
        self.time_of_last_shoot = time_of_shoot
        relative_size = min(1, elapsed / RELOAD_TIME)

        own_avatar = self.get_own_avatar()
        self.communication_client.send_reliable(messages.ShootMessage(
            player_position = own_avatar.position,
            mouse_position_world_space = own_avatar.mouse_position_world_space,
            relative_size = relative_size
        ))

    def get_own_avatar(self):
        return self.players[self.communication_client.id]
