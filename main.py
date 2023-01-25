from gameserver import GameServer
from gameclient import Client
import communication

communication.CommunicationServer().start()

client = communication.CommunicationClient()
client.send(b"Hello world!")