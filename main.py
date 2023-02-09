from gameserver import GameServer
from gameclient import GameClient
import communication

msg_storage_A, msg_storage_B = communication.MessageStorage(), communication.MessageStorage()
communication_server = communication.CommunicationServer(own_message_storage=msg_storage_A, hosting_client_message_storage=msg_storage_B, start=True)
communication_client = communication.HostingCommunicationClient(own_message_storage=msg_storage_B, server_message_storage=msg_storage_A)

game_server = GameServer(communication_server)
game_client = GameClient(communication_client)
game_server.start()

game_client.mainloop()
communication_server.stop_async()
game_server.stop()
