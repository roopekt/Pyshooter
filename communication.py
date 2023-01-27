import socket
import threading
import pickle
from dataclasses import dataclass
import messages

PORT = 29801
PUBLIC_IP = "127.0.0.1" #"195.148.39.50"
LOCAL_IP = "10.90.77.3"
MESSAGE_START = b"v!P2"

# all messages start with a header:
# - constant message start mark (32 bits)
# - content length (32bit big-endian integer)

def get_message(managed_payload):
    serialized_data = pickle.dumps(managed_payload)
    content_length_header = len(serialized_data).to_bytes(4, byteorder="big")
    return MESSAGE_START + content_length_header + serialized_data

def receive_message(socket):
    header = socket.recv(4 + 4)
    message_start = header[:4]
    assert(message_start == MESSAGE_START)
    content_length = int.from_bytes(header[4:8], byteorder="big")

    payload = socket.recv(content_length)
    return pickle.loads(payload)

class CommunicationServer:

    def __init__(self):
        self.tcp_thread = None
        self.inwards_tcp_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
        self.inwards_tcp_socket.bind(('', PORT))

        self.outwards_udp_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        self.outwards_udp_socket.bind(('', PORT))

        self.connected_players = []

    def tcp_mainloop(self):
        self.should_run = True
        with self.inwards_tcp_socket as tcp_socket:
            tcp_socket.listen()

            while self.should_run:
                connection, address = tcp_socket.accept()
                with connection:
                    message = receive_message(connection)

                    if type(message) in IMMEDIATE_MESSAGE_HANDLERS:
                        response = IMMEDIATE_MESSAGE_HANDLERS[type(message)](message, self)
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

    def send_udp(self, message):
        self.outwards_udp_socket.send(get_message(message))

class CommunicationClient:

    def __init__(self):
        self.tcp_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
        self.tcp_socket.connect((PUBLIC_IP, PORT))

    def send(self, data):
        self.tcp_socket.sendall(get_message(data))
        response = receive_message(self.tcp_socket)

    def join_server(self):
        self.send(messages.PlayerConnectionMessage(PUBLIC_IP))

@dataclass
class ServerSidePlayerHandle:
    ip: str

def handle_PlayerConnectionMessage(message: messages.PlayerConnectionMessage, server: CommunicationServer):
    server.connected_players.append(ServerSidePlayerHandle(message.ip))
    return "OK"

IMMEDIATE_MESSAGE_HANDLERS = {
    messages.PlayerConnectionMessage: handle_PlayerConnectionMessage   
}