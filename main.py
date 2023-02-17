from gameserver import GameServer
from gameclient import GameClient
import communication


communication_server = communication.CommunicationServer(start=True)

connect_directly = False
if connect_directly:
    communication_client = communication.HostingCommunicationClient(communication_server)
    communication_server.hosting_client = communication_client
else:
    communication_client = communication.InternetCommunicationClient(start=True)

game_server = GameServer(communication_server)
game_client = GameClient(communication_client)
game_server.start()

game_client.mainloop()

communication_server.stop(asyncronous=True)
if not connect_directly:
    communication_client.stop(asyncronous=True)
game_server.stop()
