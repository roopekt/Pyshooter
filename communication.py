import socket
import threading
import pickle
import messages
from random import getrandbits
from abc import ABC, abstractmethod
from queue import Queue
from typing import Union

PORT = 29801
PUBLIC_IP = "127.0.0.1" #"195.148.39.50"
LOCAL_IP = "10.90.77.3"
MESSAGE_START = b"v!P2"
RELIABLE_MESSAGE_SEND_COUNT = 3
RELIABLE_MESSAGE_ID_STORAGE_SIZE = 1024

# all messages start with a constant message start mark (32 bits)

# reliable message protocol
# - messages sent multiple times
# - receiver remembers received messages (by id) up to a limit, and only acts on first receival

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

 # with this, the hosting client and server can communicate without internet
class DirectSocket:

    def __init__(self):
        self.received_packet_queue = Queue()
        self.other_socket = None

    def recvfrom(self, max_buffer_size):
        address = "direct"
        packet = self.received_packet_queue.get()
        return packet, address

    def sendto(self, packet, address):
        self.other_socket.received_packet_queue.put(packet)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return

    @classmethod
    def get_pair(cls):
        a, b = cls(), cls()
        a.other_socket, b.other_socket = b, a
        return a, b

class ReliableMessage:

    def __init__(self, payload):
        self.id = getrandbits(32)
        self.payload = payload


def get_packet(managed_payload):
    serialized_data = pickle.dumps(managed_payload)
    return MESSAGE_START + serialized_data

# returns (data, sender's address)
def receive_message(socket: Union[socket.socket, DirectSocket]):
    data, address = socket.recvfrom(4096)
    message_start = data[:4]
    assert(message_start == MESSAGE_START)

    payload = data[4:]
    message = pickle.loads(payload)
    return message, address

class CommunicationEndpoint(ABC):

    def __init__(self, message_socket: Union[socket.socket, DirectSocket]):
        self.message_socket = message_socket
        self.message_storage = MessageStorage()
        self.should_run = False

    @abstractmethod
    def get_reliable_message_id_storage(self, sender_ip) -> ConstSizeQueue:
        pass

    @abstractmethod
    def handle_message(self, message):
        pass

    def inwards_message_mainloop(self):
        with self.message_socket as socket:
            while self.should_run:
                message, address = receive_message(socket)
                reliable_message_id_storage = self.get_reliable_message_id_storage(address)

                if isinstance(message, ReliableMessage):
                    if message.id in reliable_message_id_storage:
                        continue
                    else:
                        reliable_message_id_storage.add(message.id)
                        message = message.payload

                self.handle_message(message)

    def start(self):
        self.should_run = True
        self.inwards_message_thread = threading.Thread(target=self.inwards_message_mainloop)
        self.inwards_message_thread.start()

    def stop(self):
        if self.inwards_message_thread != None:
            self.should_run = False
            self.inwards_message_thread.join()
            self.inwards_message_thread = None

    def poll_messages(self):
        return self.message_storage.poll()

    def enqueue_message(self, message):
        self.message_storage.add(message)

class CommunicationServer(CommunicationEndpoint):

    def __init__(self, message_socket = None):
        self.connected_players: dict[str, ServerSidePlayerHandle] = {}# ip -> player

        if message_socket == None:
            message_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
            message_socket.bind(('', PORT))
        super().__init__(message_socket)

    def get_reliable_message_id_storage(self, sender_ip) -> ConstSizeQueue:
        return self.connected_players[sender_ip].reliable_message_id_storage

    def handle_message(self, message):
        if type(message) in IMMEDIATE_MESSAGE_HANDLERS:
            response = IMMEDIATE_MESSAGE_HANDLERS[type(message)](message, self)
        else:
            self.enqueue_message(message)

    def send_to_all(self, message):
        packet = get_packet(message)
        for player in self.connected_players.values():
            self.message_socket.sendto(packet, (player.ip, PORT))

    def send_to_all_reliable(self, message):
        message = ReliableMessage(message)
        for i in range(RELIABLE_MESSAGE_SEND_COUNT):
            self.send_to_all(message)

class CommunicationClient(CommunicationEndpoint):

    def __init__(self, message_socket = None):
        self.reliable_message_id_storage = ConstSizeQueue(RELIABLE_MESSAGE_ID_STORAGE_SIZE)

        if message_socket == None:
            message_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
            message_socket.bind(('', PORT))
        super().__init__(message_socket)

    def get_reliable_message_id_storage(self, sender_ip) -> ConstSizeQueue:
        return super().get_reliable_message_id_storage(sender_ip)

    def handle_message(self, message):
        self.enqueue_message(message)

    def send(self, message):
        packet = get_packet(message)
        self.message_socket.sendto(packet, (PUBLIC_IP, PORT))

    def send_reliable(self, message):
        message = ReliableMessage(message)
        for i in range(RELIABLE_MESSAGE_SEND_COUNT):
            self.send(message)

    def join_server(self):
        self.send_reliable(messages.PlayerConnectionMessage(PUBLIC_IP))

class ServerSidePlayerHandle:

    def __init__(self, player_ip):
        self.ip = player_ip
        self.reliable_message_id_storage = ConstSizeQueue(RELIABLE_MESSAGE_ID_STORAGE_SIZE)

def handle_PlayerConnectionMessage(message: messages.PlayerConnectionMessage, server: CommunicationServer):
    server.connected_players[message.ip] = ServerSidePlayerHandle(message.ip)
    return "OK"

IMMEDIATE_MESSAGE_HANDLERS = {
    messages.PlayerConnectionMessage: handle_PlayerConnectionMessage
}