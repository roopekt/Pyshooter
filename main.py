from gameserver import GameServer
from gameclient import Client
import communication

communication.CommunicationServer().start()

client = communication.CommunicationClient()
client.join_server()