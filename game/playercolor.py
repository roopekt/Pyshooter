from pygame import Color
import random

def get_pygame_color(player_name: str) -> Color:
    player_name = player_name.strip().lower()

    rng = random.Random(player_name)
    hue = rng.randrange(0, 360)

    color = Color(0, 0, 0)
    color.hsva = (hue, 100, 100, 100)
    return color

def get_hex(x: int):
    return hex(x).lstrip('0x').rjust(2, '0')

def get_pygame_gui_color(player_name: str) -> str:
    color = get_pygame_color(player_name)
    string = f"#{get_hex(color.r)}{get_hex(color.g)}{get_hex(color.b)}"
    return string
