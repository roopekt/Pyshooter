import socket
import threading
import pickle
import messages
from random import getrandbits
from abc import ABC, abstractmethod
from typing import Optional

SERVER_PORT = 29801
CLIENT_PORT = SERVER_PORT + 1
SERVER_IP = "127.0.0.1" #"195.148.39.50"
CLIENT_IP = SERVER_IP
# LOCAL_IP = "10.90.77.3"
MESSAGE_START = b"v!P2"
RELIABLE_MESSAGE_SEND_COUNT = 3
RELIABLE_MESSAGE_ID_STORAGE_SIZE = 1024

# all messages start with a constant message start mark (32 bits)

# reliable message protocol (stupid)
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

class ReliableMessage:

    def __init__(self, payload):
        self.id = getrandbits(32)
        self.payload = payload

def get_packet(managed_payload):
    serialized_data = pickle.dumps(managed_payload)
    return MESSAGE_START + serialized_data

# returns (data, sender's address)
def receive_message(socket: socket.socket):
    data, address = socket.recvfrom(4096)
    message_start = data[:4]
    assert(message_start == MESSAGE_START)

    payload = data[4:]
    message = pickle.loads(payload)
    return message, address

class CommunicationEndpoint(ABC, object):

    def __init__(self, message_socket: socket.socket, message_storage: MessageStorage):
        self.message_socket = message_socket
        self.should_run = False

        self.message_storage = message_storage

    @abstractmethod
    def get_reliable_message_id_storage(self, message: ReliableMessage, address) -> ConstSizeQueue:
        pass

    @abstractmethod
    def handle_message(self, message, address):
        pass

    def inwards_message_mainloop(self):
        with self.message_socket as socket:
            while self.should_run:
                message, address = receive_message(socket)

                if isinstance(message, ReliableMessage):
                    reliable_message_id_storage = self.get_reliable_message_id_storage(message, address)
                    if message.id in reliable_message_id_storage:
                        continue
                    else:
                        reliable_message_id_storage.add(message.id)
                        message = message.payload

                self.handle_message(message, address)

    def start(self):
        self.should_run = True
        self.inwards_message_thread = threading.Thread(target=self.inwards_message_mainloop, daemon=True)
        self.inwards_message_thread.start()

    def stop_async(self):
        if self.inwards_message_thread != None:
            self.should_run = False

    def poll_messages(self):
        return self.message_storage.poll()

    def enqueue_message(self, message):
        self.message_storage.add(message)

class CommunicationServer(CommunicationEndpoint):

    def __init__(self, start = False):
        self.hosting_client: Optional[HostingCommunicationClient] = None
        self.connected_players: dict[messages.ObjectId, ServerSidePlayerHandle] = {}
        message_storage = MessageStorage()

        message_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        message_socket.bind((SERVER_IP, SERVER_PORT))

        super().__init__(message_socket, message_storage)

        if start:
            self.start()

    def get_reliable_message_id_storage(self, message, address) -> ConstSizeQueue:
        player_id = message.payload.sender_id
        self.add_player_if_new(player_id, address)
        return self.connected_players[player_id].reliable_message_id_storage

    def handle_message(self, message, address):
        assert(isinstance(message, messages.MessageToServerWithId))
        self.add_player_if_new(message.sender_id, address)
        self.enqueue_message(message)

    def add_player_if_new(self, player_id: messages.ObjectId, address):
        known_ids = list(self.connected_players.keys())
        if self.hosting_client != None:
            known_ids.append(self.hosting_client.id)

        if player_id not in known_ids:
            self.connected_players[player_id] = ServerSidePlayerHandle(player_id, address[0])

    def send_to_all(self, message):
        packet = get_packet(message)
        for player in self.connected_players.values():
            self.message_socket.sendto(packet, (player.ip, CLIENT_PORT))

        if self.hosting_client != None:
            self.hosting_client.handle_message(message)

    def send_to_all_reliable(self, message):
        message = ReliableMessage(message)
        for i in range(RELIABLE_MESSAGE_SEND_COUNT):
            self.send_to_all(message)

class CommunicationClient(ABC, object):

    def __init__(self):
        self.id = messages.get_new_object_id()

    @abstractmethod
    def send(self, message):
        pass

    @abstractmethod
    def send_reliable(self, message):
        pass

    @abstractmethod
    def poll_messages(self) -> list[messages.MessageToClient]:
        pass

class InternetCommunicationClient(CommunicationEndpoint, CommunicationClient):

    def __init__(self, start = False):
        CommunicationClient.__init__(self)
        self.reliable_message_id_storage = ConstSizeQueue(RELIABLE_MESSAGE_ID_STORAGE_SIZE)

        message_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        message_socket.bind((CLIENT_IP, CLIENT_PORT))
        CommunicationEndpoint.__init__(self, message_socket, MessageStorage())

        if start:
            self.start()

    def get_reliable_message_id_storage(self, message, address) -> ConstSizeQueue:
        return self.reliable_message_id_storage

    def handle_message(self, message, address):
        assert(isinstance(message, messages.MessageToClient))
        self.enqueue_message(message)

    def send(self, message):
        packet = get_packet(messages.MessageToServerWithId(self.id, message))
        self.message_socket.sendto(packet, (SERVER_IP, SERVER_PORT))

    def send_reliable(self, message):
        packet = get_packet(ReliableMessage(messages.MessageToServerWithId(self.id, message)))
        for i in range(RELIABLE_MESSAGE_SEND_COUNT):
            self.message_socket.sendto(packet, (SERVER_IP, SERVER_PORT))

# on the same machine as server, doesn't need internet
class HostingCommunicationClient(CommunicationClient):

    def __init__(self, server: CommunicationServer):
        super().__init__()
        self.server = server
        self.message_storage = MessageStorage()

    def handle_message(self, message: messages.MessageToClient):
        self.message_storage.add(message)

    def send(self, message):
        message = messages.MessageToServerWithId(self.id, message)
        self.server.handle_message(message, ("direct", 0))

    def send_reliable(self, message):
        self.send(message)

    def poll_messages(self):
        return self.message_storage.poll()

class ServerSidePlayerHandle:

    def __init__(self, player_id: messages.ObjectId, ip: str):
        self.id = player_id
        self.ip = ip
        self.reliable_message_id_storage = ConstSizeQueue(RELIABLE_MESSAGE_ID_STORAGE_SIZE)
