import socket
import threading
import pickle
import messages
from random import getrandbits
from abc import ABC, abstractmethod

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

class CommunicationEndpoint(ABC):

    def __init__(self, message_socket: socket.socket, message_storage: MessageStorage):
        self.message_socket = message_socket
        self.should_run = False

        self.message_storage = message_storage

    @abstractmethod
    def get_reliable_message_id_storage(self, message: ReliableMessage) -> ConstSizeQueue:
        pass

    @abstractmethod
    def handle_message(self, message):
        pass

    def inwards_message_mainloop(self):
        with self.message_socket as socket:
            while self.should_run:
                message, address = receive_message(socket)

                if isinstance(message, ReliableMessage):
                    reliable_message_id_storage = self.get_reliable_message_id_storage(message)
                    if message.id in reliable_message_id_storage:
                        continue
                    else:
                        reliable_message_id_storage.add(message.id)
                        message = message.payload

                self.handle_message(message)

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

    def __init__(self, own_message_storage = None, hosting_client_message_storage = None, start = False):
        self.hosting_client_message_storage = hosting_client_message_storage
        self.connected_players: dict[messages.PlayerId, ServerSidePlayerHandle] = {}

        if own_message_storage == None:
            own_message_storage = MessageStorage()

        message_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        message_socket.bind(('', PORT))

        super().__init__(message_socket, own_message_storage)

        if start:
            self.start()

    def get_reliable_message_id_storage(self, message) -> ConstSizeQueue:
        player_id = message.payload.player_id
        return self.connected_players[player_id].reliable_message_id_storage

    def handle_message(self, message):
        assert(isinstance(message, messages.MessageToServerWithId))
        message_type = type(message.payload)

        if message_type in IMMEDIATE_MESSAGE_HANDLERS:
            response = IMMEDIATE_MESSAGE_HANDLERS[message_type](message.payload, message.sender_id, self)

        self.enqueue_message(message)

    def send_to_all(self, message):
        packet = get_packet(message)
        for player in self.connected_players.values():
            self.message_socket.sendto(packet, (player.ip, PORT))

        if self.hosting_client_message_storage != None:
            self.hosting_client_message_storage.add(message)

    def send_to_all_reliable(self, message):
        message = ReliableMessage(message)
        for i in range(RELIABLE_MESSAGE_SEND_COUNT):
            self.send_to_all(message)

class CommunicationClient(ABC):

    def __init__(self):
        self.id = messages.get_new_player_id()

    @abstractmethod
    def send(self, message):
        pass

    @abstractmethod
    def send_reliable(self, message):
        pass

    @abstractmethod
    def poll_messages(self) -> list[messages.MessageToClient]:
        pass

    def join_server(self):
        self.send_reliable(messages.PlayerConnectionMessage())

class InternetCommunicationClient(CommunicationEndpoint, CommunicationClient):

    def __init__(self, start = False):
        super(CommunicationClient, self).__init__()
        self.reliable_message_id_storage = ConstSizeQueue(RELIABLE_MESSAGE_ID_STORAGE_SIZE)

        message_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        message_socket.bind(('', PORT))
        super(CommunicationEndpoint, self).__init__(message_socket, MessageStorage())

        if start:
            self.start()

    def get_reliable_message_id_storage(self, message) -> ConstSizeQueue:
        return self.reliable_message_id_storage

    def handle_message(self, message):
        assert(isinstance(message, messages.MessageToClient))
        self.enqueue_message(message)

    def send(self, message):
        message = messages.MessageToServerWithId(self.id, message)
        packet = get_packet(message)
        self.message_socket.sendto(packet, (PUBLIC_IP, PORT))

    def send_reliable(self, message):
        message = ReliableMessage(message)
        for i in range(RELIABLE_MESSAGE_SEND_COUNT):
            self.send(message)

    def join_server(self):
        self.send_reliable(messages.PlayerConnectionMessage())

# on the same machine as server, doesn't need internet
class HostingCommunicationClient(CommunicationClient):

    def __init__(self, own_message_storage: MessageStorage, server_message_storage: MessageStorage):
        super().__init__()
        self.own_message_storage = own_message_storage
        self.server_message_storage = server_message_storage

    def send(self, message):
        message = messages.MessageToServerWithId(self.id, message)
        self.server_message_storage.add(message)

    def send_reliable(self, message):
        self.send(message)

    def poll_messages(self):
        return self.own_message_storage.poll()

class ServerSidePlayerHandle:

    def __init__(self, player_id: messages.PlayerId):
        self.ip = player_id
        self.reliable_message_id_storage = ConstSizeQueue(RELIABLE_MESSAGE_ID_STORAGE_SIZE)

def handle_PlayerConnectionMessage(message: messages.PlayerConnectionMessage, player_id: messages.PlayerId, server: CommunicationServer):
    server.connected_players[player_id] = ServerSidePlayerHandle(player_id)
    return "OK"

IMMEDIATE_MESSAGE_HANDLERS = {
    messages.PlayerConnectionMessage: handle_PlayerConnectionMessage
}