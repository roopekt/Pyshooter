from gameserver import GameServer
from gameclient import GameClient
import communication

msg_storage_A, msg_storage_B = communication.MessageStorage(), communication.MessageStorage()
communication_server = communication.CommunicationServer(start=True)
communication_client = communication.HostingCommunicationClient(communication_server)
communication_server.hosting_client = communication_client

game_server = GameServer(communication_server)
game_client = GameClient(communication_client)
game_server.start()

game_client.mainloop()
communication_server.stop_async()
game_server.stop()
