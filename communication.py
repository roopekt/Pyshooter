import socket
import threading
import pickle
from dataclasses import dataclass, field
import messages
from random import getrandbits

PORT = 29801
PUBLIC_IP = "127.0.0.1" #"195.148.39.50"
LOCAL_IP = "10.90.77.3"
MESSAGE_START = b"v!P2"
RELIABLE_MESSAGE_SEND_COUNT = 3

# all messages start with a header:
# - constant message start mark (32 bits)
# - content length (32bit big-endian integer)

# reliable message protocol
# - messages sent multiple times
# - receiver remembers received messages (by id) up to a limit, and only acts on first receival

def get_message(managed_payload):
    serialized_data = pickle.dumps(managed_payload)
    content_length_header = len(serialized_data).to_bytes(4, byteorder="big")
    return MESSAGE_START + content_length_header + serialized_data

# returns (data, sender's address)
def receive_message(socket: socket.socket):
    data, address = socket.recvfrom(4096)
    message_start = data[:4]
    assert(message_start == MESSAGE_START)
    content_length = int.from_bytes(data[4:8], byteorder="big")

    payload = data[8:]
    return pickle.loads(payload), address

class MessageStorage:

    def __init__(self):
        self.lock = threading.Lock()
        self.messages = []

    def add(self, message):
        with self.lock:
            self.messages.append(message)

    def poll(self):
        with self.lock:
            messages = self.messages
            self.messages = []
        return messages

class ConstSizeQueue:

    def __init__(self, size):
        self.size = size
        self.array = [None] * size
        self.next_item_index = 0

    def add(self, item):
        self.array[self.next_item_index] = item

        self.next_item_index += 1
        self.next_item_index %= self.size

    def __len__(self):
        return self.size

    def __contains__(self, item):
        return item in self.array

class ReliableMessage:

    def __init__(self, payload):
        self.id = getrandbits(32)
        self.payload = payload

class CommunicationServer:

    def __init__(self):
        self.inwards_message_thread = None
        self.message_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        self.message_socket.bind(('', PORT))

        self.connected_players: dict[str, ServerSidePlayerHandle] = {}# ip -> player
        self.message_storage = MessageStorage()

    def inwards_message_mainloop(self):
        with self.message_socket as socket:
            while self.should_run:
                message, address = receive_message(socket)
                sender = self.connected_players[address]

                if isinstance(message, ReliableMessage):
                    if sender.has_received(message):
                        continue
                    else:
                        sender.mark_received_reliable_message(message)
                        message = message.payload

                if type(message) in IMMEDIATE_MESSAGE_HANDLERS:
                    response = IMMEDIATE_MESSAGE_HANDLERS[type(message)](message, self)
                else:
                    self.message_storage.add(message)

    def start(self):
        assert(self.inwards_message_thread == None)
        self.should_run = True
        self.inwards_message_thread = threading.Thread(target=self.inwards_message_mainloop)
        self.inwards_message_thread.start()

    def stop(self):
        if self.inwards_message_thread != None:
            self.should_run = False
            self.inwards_message_thread.join()
            self.inwards_message_thread = None

    def send(self, message):
        self.message_socket.send(get_message(message))

    def send_reliable(self, message):
        message = get_message(ReliableMessage(message))
        for i in range(RELIABLE_MESSAGE_SEND_COUNT):
            self.message_socket.send(message)

    def poll_messages(self):
        return self.message_storage.poll()

class CommunicationClient:

    def __init__(self):
        self.inwards_message_thread = None
        self.message_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        self.message_socket.bind(('', PORT))

        self.message_storage = MessageStorage()
        self.received_reliable_message_ids = []

    def inwards_message_mainloop(self):
        with self.message_socket as socket:
            while self.should_run:
                message = receive_message(socket)

                if isinstance(message, ReliableMessage):
                    if message.id in self.received_reliable_message_ids:
                        continue
                    else:
                        self.received_reliable_message_ids.append(message.id)
                        message = message.payload

                self.message_storage.add(message)

    def start(self):
        assert(self.inwards_message_thread == None)
        self.should_run = True
        self.inwards_message_thread = threading.Thread(target=self.inwards_message_mainloop)
        self.inwards_message_thread.start()

    def stop(self):
        if self.inwards_message_thread != None:
            self.should_run = False
            self.inwards_message_thread.join()
            self.inwards_message_thread = None

    def send(self, message):
        self.message_socket.send(get_message(message))

    def send_reliable(self, message):
        message = get_message(ReliableMessage(message))
        for i in range(RELIABLE_MESSAGE_SEND_COUNT):
            self.message_socket.send(message)

    def poll_messages(self):
        return self.message_storage.poll()

    def join_server(self):
        self.send_reliable(messages.PlayerConnectionMessage(PUBLIC_IP))

class ServerSidePlayerHandle:

    def __init__(self, player_ip):
        self.ip = player_ip
        self.received_reliable_message_ids = ConstSizeQueue(1024)

    def has_received(self, reliable_message: ReliableMessage):
        return reliable_message.id in self.received_reliable_message_ids

    def mark_received_reliable_message(self, reliable_message: ReliableMessage):
        self.received_reliable_message_ids.add(reliable_message.id)

def handle_PlayerConnectionMessage(message: messages.PlayerConnectionMessage, server: CommunicationServer):
    server.connected_players[message.ip] = ServerSidePlayerHandle(message.ip)
    return "OK"

IMMEDIATE_MESSAGE_HANDLERS = {
    messages.PlayerConnectionMessage: handle_PlayerConnectionMessage
}