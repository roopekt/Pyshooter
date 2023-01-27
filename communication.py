import socket
import threading
from dataclasses import dataclass
import pickle
from abc import ABC, abstractmethod

PORT = 29801
PUBLIC_IP = "127.0.0.1" #"195.148.39.50"
LOCAL_IP = "10.90.77.3"

# all messages start with a 32 bit header representing content length in bytes
def get_message(managed_payload):
    serialized_data = pickle.dumps(managed_payload)
    header = len(serialized_data).to_bytes(4, byteorder="big")
    return header + serialized_data

def receive_message(socket):
    content_length = int.from_bytes(socket.recv(4), byteorder="big")
    payload = socket.recv(content_length)
    return pickle.loads(payload)

class CommunicationServer:

    def __init__(self):
        self.tcp_thread = None
        self.tcp_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
        self.tcp_socket.bind(('', PORT))

        # self.udp_socket = socket.socket(family=socket.AF_INET6, type=socket.SOCK_DGRAM)
        # self.udp_socket.bind(("", 4242))

        self.connected_players = []

    def tcp_mainloop(self):
        self.should_run = True
        with self.tcp_socket as tcp_socket:
            tcp_socket.listen()

            while self.should_run:
                connection, address = tcp_socket.accept()
                with connection:
                    task = receive_message(connection)
                    response = task.run(self)
                    connection.sendall(get_message(response))

    def start(self):
        assert(self.tcp_thread == None)
        self.tcp_thread = threading.Thread(target=self.tcp_mainloop)
        self.tcp_thread.start()

    def stop(self):
        if self.tcp_thread != None:
            self.should_run = False
            self.tcp_thread.join()
            self.tcp_thread = None

class CommunicationClient:

    def __init__(self):
        self.tcp_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
        self.tcp_socket.connect((PUBLIC_IP, PORT))

    def send(self, data):
        self.tcp_socket.sendall(get_message(data))
        response = receive_message(self.tcp_socket)

    def join_server(self):
        self.send(PlayerConnectionMessage(PUBLIC_IP))

class ServerTask(ABC):

    @abstractmethod
    def run(self, server: CommunicationServer):
        pass

@dataclass
class PlayerConnectionMessage(ServerTask):
    ip: str

    def run(self, server):
        server.connected_players.append(ServerSidePlayerHandle(self.ip))
        return "OK"

@dataclass
class ServerSidePlayerHandle:
    ip: str