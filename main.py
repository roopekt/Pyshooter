from gameserver import GameServer
from gameclient import GameClient
import communication

communication.CommunicationServer().start()

client = communication.CommunicationClient()
client.join_server()

server = GameServer()
client = GameClient(server)
server.start()
client.mainloop()
server.stop()
