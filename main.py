import argumentparser
from sys import argv
import gameparameters
from random import randint

arguments = None
if len(argv) > 1:
    arguments = argumentparser.get_arguments()

    if arguments.local_ip == None:
        arguments.local_ip = gameparameters.get_local_ip()

import pygame
import scenemanager

SERVER_PORT = 29800
client_port = SERVER_PORT + randint(1, 1023)
window = pygame.display.set_mode((640, 480), pygame.RESIZABLE)

scenemanager.SceneManager(window, SERVER_PORT, client_port).mainloop(start_with_parameters=arguments)
