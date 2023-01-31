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
    data = socket.recv(4096)
    message_start = data[:4]
    assert(message_start == MESSAGE_START)
    content_length = int.from_bytes(data[4:8], byteorder="big")

    payload = data[8:]
    return pickle.loads(payload)

class CommunicationServer:

    def __init__(self):
        self.inwards_udp_thread = None
        self.udp_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        self.udp_socket.bind(('', PORT))

        self.connected_players = []

    def inwards_udp_mainloop(self):
        self.should_run = True
        with self.udp_socket as socket:
            while self.should_run:
                message = receive_message(socket)

                if type(message) in IMMEDIATE_MESSAGE_HANDLERS:
                    response = IMMEDIATE_MESSAGE_HANDLERS[type(message)](message, self)
                    # socket.sendall(get_message(response))

    def start(self):
        assert(self.inwards_udp_thread == None)
        self.inwards_udp_thread = threading.Thread(target=self.inwards_udp_mainloop)
        self.inwards_udp_thread.start()

    def stop(self):
        if self.inwards_udp_thread != None:
            self.should_run = False
            self.inwards_udp_thread.join()
            self.inwards_udp_thread = None

    def send_udp(self, message):
        self.udp_socket.send(get_message(message))

class CommunicationClient:

    def __init__(self):
        self.udp_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        self.udp_socket.connect((PUBLIC_IP, PORT))
        self.inwards_udp_thread = None

    def send(self, data):
        self.udp_socket.sendall(get_message(data))
        # response = receive_message(self.outwards_udp_socket)

    def join_server(self):
        self.send(messages.PlayerConnectionMessage(PUBLIC_IP))

    def receiving_udp_mainloop(self):
        self.should_run = True
        with self.udp_socket as socket:
            while self.should_run:
                message = receive_message(socket)

    def start(self):
        assert(self.inwards_udp_thread == None)
        self.inwards_udp_thread = threading.Thread(target=self.receiving_udp_mainloop)
        self.inwards_udp_thread.start()

    def stop(self):
        if self.inwards_udp_thread != None:
            self.should_run = False
            self.inwards_udp_thread.join()
            self.inwards_udp_thread = None

@dataclass
class ServerSidePlayerHandle:
    ip: str

def handle_PlayerConnectionMessage(message: messages.PlayerConnectionMessage, server: CommunicationServer):
    server.connected_players.append(ServerSidePlayerHandle(message.ip))
    return "OK"

IMMEDIATE_MESSAGE_HANDLERS = {
    messages.PlayerConnectionMessage: handle_PlayerConnectionMessage   
}