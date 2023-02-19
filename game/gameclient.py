import pygame
from pygame import Color
from communication import CommunicationClient
import messages
from . import player, bullet
from time import time
from .camera import Camera
from .background import Background

MAX_FPS = 60
RELOAD_TIME = 1 # in seconds

class GameClient:

    def __init__(self, communication_client: CommunicationClient):
        self.communication_client = communication_client

        self.players = {
            self.communication_client.id : player.ClientPlayer(is_owned_by_client=True)
        }
        self.bullets: dict[messages.ObjectId, bullet.ClientBullet] = {}
        self.time_of_last_shoot = time()

        pygame.init()
        self.window = pygame.display.set_mode((640, 480), pygame.RESIZABLE)
        self.background = Background()
        self.camera = Camera(self.window)

    def mainloop(self):
        self.should_run = True
        clock = pygame.time.Clock()

        while self.should_run:
            clock.tick(MAX_FPS)
            self.handle_input()
            self.handle_messages()
            self.update_camera()
            self.send_post_frame_messages()
            self.render()

        pygame.quit()

    def handle_input(self):
        self.get_own_avatar().mouse_position_world_space = self.camera.get_world_position(pygame.mouse.get_pos())

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.should_run = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self.shoot()

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
            else:
                raise Exception(f"Client cannot handle a {type(message)}.")

    def update_camera(self):
        self.camera.position = self.get_own_avatar().position

    def send_post_frame_messages(self):
        self.communication_client.send(messages.MousePositionUpdate(self.get_own_avatar().mouse_position_world_space))

    def render(self):
        graphic_scaler = self.camera.get_graphical_scale_factor()
        self.window.fill(Color("black"))
        self.background.render(self.camera)

        for _player in self.players.values():
            if _player.position != None:
                pygame.draw.circle(
                    self.window,
                    Color(255, 0, 0),
                    self.camera.get_screen_position(_player.position),
                    player.RADIUS * graphic_scaler
                )
                gun_pos = _player.position + (_player.mouse_position_world_space - _player.position).scale_to_length(player.RADIUS)
                pygame.draw.circle(
                    self.window,
                    Color(255, 255, 0),
                    self.camera.get_screen_position(gun_pos),
                    player.RADIUS * graphic_scaler / 3
                )

        for _bullet in self.bullets.values():
            pygame.draw.circle(
                self.window,
                Color("white"),
                self.camera.get_screen_position(_bullet.position),
                _bullet.radius * graphic_scaler
            )

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