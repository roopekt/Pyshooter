import pygame
from pygame import Color
from communication import CommunicationClient
import messages
import player
from pymunk import Vec2d
import mymath

MAX_FPS = 60

class GameClient:

    def __init__(self, communication_client: CommunicationClient):
        self.communication_client = communication_client
        self.camera_position = Vec2d.zero()
        self.camera_height = 15

        self.players = {
            self.communication_client.id : player.ClientPlayer(is_owned_by_client=True)
        }

    def mainloop(self):
        pygame.init()

        self.should_run = True
        clock = pygame.time.Clock()
        self.window = pygame.display.set_mode((640, 480), pygame.RESIZABLE)

        while self.should_run:
            clock.tick(MAX_FPS)
            self.handle_input()
            self.handle_messages()
            self.render()

        pygame.quit()

    def handle_input(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.should_run = False

        self.get_own_avatar().mouse_position_world_space = self.get_world_position(pygame.mouse.get_pos())

    def handle_messages(self):
        for message in self.communication_client.poll_messages():
            if isinstance(message, messages.PlayerStateUpdate):
                self.players[message.player_id].update_state(message)
            else:
                raise Exception(f"Client cannot handle a {type(message)}.")

    def send_post_frame_messages(self):
        self.communication_client.send(messages.MousePositionUpdate(self.get_own_avatar().mouse_position_world_space))

    def render(self):
        graphic_scaler = self.get_graphical_scale_factor()
        self.window.fill(Color(0, 0, 0))

        for _player in self.players.values():
            if _player.position != None:
                pygame.draw.circle(
                    self.window,
                    Color(255, 0, 0),
                    self.get_screen_position(_player.position),
                    player.RADIUS * graphic_scaler
                )
                gun_pos = _player.position + (_player.mouse_position_world_space - _player.position).scale_to_length(player.RADIUS)
                pygame.draw.circle(
                    self.window,
                    Color(255, 255, 0),
                    self.get_screen_position(gun_pos),
                    player.RADIUS * graphic_scaler / 3
                )

        pygame.display.flip()

    def get_screen_position(self, world_position: Vec2d):
        window_size = mymath.tuple_to_pymunk_vec(self.window.get_size())

        p = world_position - self.camera_position
        p = Vec2d(p.x, -p.y)
        p *= self.get_graphical_scale_factor()
        p += window_size / 2
        return pygame.Vector2(p.x, p.y)

    def get_world_position(self, screen_position: tuple[float, float]):
        window_size = mymath.tuple_to_pymunk_vec(self.window.get_size())

        p = mymath.tuple_to_pymunk_vec(screen_position)
        p -= window_size / 2
        p /= self.get_graphical_scale_factor()
        p = Vec2d(p.x, -p.y)
        p += self.camera_position
        return p

    # scale factor to convert between world units and pixels
    def get_graphical_scale_factor(self):
        return self.window.get_height() / self.camera_height

    def get_own_avatar(self):
        return self.players[self.communication_client.id]
