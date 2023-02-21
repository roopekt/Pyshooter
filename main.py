import argumentparser
from sys import argv
import ipfinder

if len(argv) > 1:
    arguments = argumentparser.get_arguments()

    if arguments.local_ip == None:
        arguments.local_ip = ipfinder.get_local_ip()
else:
    arguments = argumentparser.ParsedArguments(
        is_host = True,
        local_ip = "127.0.0.1",
        remote_server_ip = "127.0.0.1"
    )

from game.gameserver import GameServer
from game.gameclient import GameClient
import communication
from pygame import quit as quit_pygame
from random import randint

SERVER_PORT = 29800
client_port = SERVER_PORT + randint(1, 1023)

if arguments.is_host:
    communication_server = communication.CommunicationServer((arguments.local_ip, SERVER_PORT), start=True)
    game_server = GameServer(communication_server, start=True)

    communication_client = communication.HostingCommunicationClient(communication_server)
    communication_server.hosting_client = communication_client

    game_client = GameClient(communication_client)
    game_client.mainloop()

    communication_server.stop(asyncronous=True)
    game_server.stop()
else:
    communication_client = communication.InternetCommunicationClient(
        (arguments.local_ip, client_port),
        (arguments.remote_server_ip, SERVER_PORT),
        start=True
    )

    game_client = GameClient(communication_client)
    game_client.mainloop()

    communication_client.stop(asyncronous=True)

quit_pygame()
