import pygame
from communication import CommunicationClient
import messages
from . import player, bullet, playercolor
from time import time
from .camera import Camera
from .background import Background
import scene
from .arena import ClientArena
from windowcontainer import WindowContainer
from . import sprite
from pymunk import Vec2d
from collections import Counter
from pygame import freetype

RELOAD_TIME = 0.7 # in seconds
HUD_ICON_WIDTH = 20
WIN_MESSAGE_FONT = freetype.SysFont("verdana", 100)
GO_TO_LOBBY_MESSAGE_FONT = freetype.SysFont("calibri", 15, bold=True)

class GameClient(scene.Scene):

    def __init__(self, communication_client: CommunicationClient, window_container: WindowContainer, name: str):
        super().__init__(window_container, max_fps=60)
        self.communication_client = communication_client
        self.communication_client.remove_messages_of_other_types(messages.GameMessage)
        self.name = name

        self.players = {
            self.communication_client.id : player.ClientPlayer(is_owned_by_client=True, name=self.name)
        }
        self.bullets: dict[messages.ObjectId, bullet.ClientBullet] = {}
        self.time_of_last_shoot = time()
        self.arena = ClientArena()

        pygame.init()
        self.window = window_container
        self.background = Background()
        self.camera = Camera(self.window)

        self.damage_icon_sprite = sprite.Sprite("assets/sword.png",  HUD_ICON_WIDTH, transparent=True, screen_space=True, pivot="tl-corner")
        self.recoil_icon_sprite = sprite.Sprite("assets/recoil.png", HUD_ICON_WIDTH, transparent=True, screen_space=True, pivot="tl-corner")

        self.communication_client.send_reliable(messages.JoinGameMessage(self.name))

    def handle_events(self, events: list[pygame.event.Event]):
        self.get_own_avatar().mouse_position_world_space = self.camera.get_world_position(pygame.mouse.get_pos())

        for event in events:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.scene_to_switch_to = scene.SCENE_STARTMENU
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.get_own_avatar().health > 0:
                    self.shoot()
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                if self.has_game_ended():
                    self.communication_client.send_reliable(messages.GoToLobbyRequest())

    def update(self):
        self.handle_messages()
        self.update_camera()
        self.send_post_frame_messages()

    def handle_messages(self):
        for message in self.communication_client.poll_messages(type_to_poll=messages.GameMessage):
            if isinstance(message, messages.NewPlayerNotification):
                if message.player_id not in self.players:
                    self.players[message.player_id] = player.ClientPlayer(is_owned_by_client=False)

                self.players[message.player_id].name = message.player_name
            elif isinstance(message, messages.PlayerStateUpdate):
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
            elif isinstance(message, messages.ArenaUpdate):
                self.arena.handle_arena_update(message)
            elif isinstance(message, messages.GoToLobbyNotification):
                self.scene_to_switch_to = scene.SCENE_LOBBY
            else:
                raise Exception(f"Client cannot handle a {type(message)}.")

    def update_camera(self):
        own_avatar = self.get_own_avatar()
        other_players = dict(self.players)
        other_players.pop(self.communication_client.id)
        self.camera.update(own_avatar.head_position, [p.head_position for p in other_players.values()])

    def send_post_frame_messages(self):
        self.communication_client.send(messages.MousePositionUpdate(self.get_own_avatar().mouse_position_world_space))

    def render(self):
        self.background.render(self.camera)

        for _bullet in self.bullets.values():
            _bullet.render(self.camera)
        self.arena.render(self.camera)
        for _player in self.players.values():
            _player.render(self.camera)
        self.render_HUD()

        if self.has_game_ended():
            self.render_end_screen()

        pygame.display.flip()

    def shoot(self):
        bullet_relative_size = self.get_bullet_relative_size()
        self.time_of_last_shoot = time()

        own_avatar = self.get_own_avatar()
        self.communication_client.send_reliable(messages.ShootMessage(
            initial_bullet_position = own_avatar.left_arm_position,
            mouse_position_world_space = own_avatar.mouse_position_world_space,
            relative_size = bullet_relative_size
        ))

    def get_bullet_relative_size(self):
        now = time()
        elapsed = now - self.time_of_last_shoot
        return min(1, elapsed / RELOAD_TIME)

    def get_own_avatar(self):
        return self.players[self.communication_client.id]

    def render_HUD(self):
        bullet_relative_size = self.get_bullet_relative_size()
        relative_damage = bullet_relative_size**2
        relative_recoil = bullet_relative_size**player.RECOIL_EXPONENT
        corner = self.camera.get_top_left_corner_world_space()

        padding = 5
        bar_thickness = 6
        bar_length = 100

        self.damage_icon_sprite.render(self.camera, Vec2d(padding, padding))
        self.recoil_icon_sprite.render(self.camera, Vec2d(padding, padding + HUD_ICON_WIDTH))

        damage_rect = pygame.Rect((2*padding + HUD_ICON_WIDTH, padding + 0.5*HUD_ICON_WIDTH - bar_thickness/2), (bar_length * relative_damage, bar_thickness))
        recoil_rect = pygame.Rect((2*padding + HUD_ICON_WIDTH, padding + 1.5*HUD_ICON_WIDTH - bar_thickness/2), (bar_length * relative_recoil, bar_thickness))

        color = pygame.Color("black") if bullet_relative_size >= 1 else pygame.Color("white")

        pygame.draw.rect(
            self.camera.window_container.window,
            color,
            damage_rect
        )
        pygame.draw.rect(
            self.camera.window_container.window,
            color,
            recoil_rect
        )

    def has_game_ended(self):
        enough_dead = Counter([p.is_alive() for p in self.players.values()])[True] <= 1
        multiple_players = len(self.players) > 1
        return enough_dead and multiple_players

    def render_end_screen(self):
        alive_players = [p for p in self.players.values() if p.is_alive()]
        assert len(alive_players) <= 1, f"Game ended when {len(alive_players)} players still alive."
        if len(alive_players) == 0:
            print("WARNING: everyone is dead")

        center = self.camera.get_window_size() / 2

        # render win text
        if len(alive_players) == 1:
            winner_name = alive_players[0].name
            win_text = f"{winner_name} won!"

            text_pos = center + pygame.Vector2(0, -80)
            text_rect = WIN_MESSAGE_FONT.get_rect(win_text)
            text_pos -= pygame.Vector2(text_rect.width / 2, 0)
            WIN_MESSAGE_FONT.render_to(
                self.camera.window_container.window,
                text_pos,
                win_text,
                fgcolor=playercolor.get_pygame_color(winner_name)
            )

        #render instructions for going to lobby
        text = "Press Enter to enter lobby."
        text_pos = center
        text_rect = GO_TO_LOBBY_MESSAGE_FONT.get_rect(text)
        text_pos -= pygame.Vector2(text_rect.width / 2, 0)
        GO_TO_LOBBY_MESSAGE_FONT.render_to(
            self.camera.window_container.window,
            text_pos,
            text,
            fgcolor=pygame.Color("white")
        )


