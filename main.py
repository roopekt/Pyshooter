from server import Server
from client import Client

server = Server()
server.start()

client = Client()
client.mainloop()

server.stop()