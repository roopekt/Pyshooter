from gameserver import GameServer
from gameclient import GameClient
import communication
import argument_parser

arguments = argument_parser.get_arguments()

if not arguments.client_only:
    communication_server = communication.CommunicationServer(start=True)
    game_server = GameServer(communication_server)
    game_server.start()

if arguments.connect_directly:
    communication_client = communication.HostingCommunicationClient(communication_server)
    communication_server.hosting_client = communication_client
else:
    communication_client = communication.InternetCommunicationClient(start=True)

game_client = GameClient(communication_client)
game_client.mainloop()

if not arguments.client_only:
    communication_server.stop(asyncronous=True)
    game_server.stop()
if not arguments.connect_directly:
    communication_client.stop(asyncronous=True)
