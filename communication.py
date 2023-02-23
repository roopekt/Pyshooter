import socket
import threading
from thread_owner import ThreadOwner
import pickle
import messages
from random import getrandbits, random
from abc import ABC, abstractmethod
from typing import Optional
from dataclasses import dataclass, field
from time import time, sleep
import copy

MESSAGE_START = b"v!P2"
RELIABLE_MESSAGE_INITIAL_SEND_COUNT = 2
RELIABLE_MESSAGE_ID_STORAGE_SIZE = 1024
RELIABLE_MESSAGE_RESEND_DELAY = 30 #in milli seconds
RESEND_MESSAGE_RESEND_ITERATION_DELAY = 15

# all messages start with a constant message start mark (32 bits)

# reliable communicatin protocol:
# at first, the message (ReliableMessage) is sent multiple times
# if the receiver receives the message, it sends a confirmation (MessageConfirmation)
# the message is resent on regular intervals, until a confirmation is received
# the receiver remembers recently received messages (by id), and only acts on the first message

SIMULATED_PACKAGE_LOSS_PERCENTAGE = 0
if float(SIMULATED_PACKAGE_LOSS_PERCENTAGE) != 0.0:
    print(f"Simulated package loss of {SIMULATED_PACKAGE_LOSS_PERCENTAGE} %")

class ReceivedMessageStorage:

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

@dataclass
class ReliableMessage:
    payload: ...
    id: int = field(init=False)


    def __post_init__(self):
        self.id = getrandbits(32)

@dataclass
class MessageConfirmation:
    message_id: int

@dataclass
class UnconfirmedMessage:
    message: ReliableMessage
    address: tuple[str, int]
    last_send_time: float = field(init=False)
    
    def __post_init__(self):
        self.last_send_time = time()
    
class UncofirmedMessageStorage:

    def __init__(self):
        self.unconfirmed_messages: dict[int, UnconfirmedMessage] = {}
        self.lock = threading.Lock()

    def recieve_confirmation(self, confirmation: MessageConfirmation):
        with self.lock:
            if confirmation.message_id in self.unconfirmed_messages:
                self.unconfirmed_messages.pop(confirmation.message_id)

    def add_message(self, message: ReliableMessage, address):
        with self.lock:
            self.unconfirmed_messages[message.id] = UnconfirmedMessage(message, address)

    def get_messages(self):
        with self.lock:
            return list(self.unconfirmed_messages.values())

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

class CommunicationEndpoint(ThreadOwner, ABC):

    def __init__(self, message_socket: socket.socket, message_storage: ReceivedMessageStorage, thread_name: str):
        self.message_socket = message_socket
        self.message_storage = message_storage # unhandled received messages
        self.unconfirmed_message_storage = UncofirmedMessageStorage() # sent unconfirmed reliable messages
 
        ThreadOwner.__init__(self)
        self.add_thread(threading.Thread(target=self.inwards_message_mainloop, daemon=True), thread_name)
        self.add_thread(threading.Thread(target=self.reliable_message_resend_mainloop, daemon=True), f"{thread_name} confirmation")
        self.send_lock = threading.Lock()

    @abstractmethod
    def get_reliable_message_id_storage(self, message: ReliableMessage, address) -> ConstSizeQueue:
        pass

    @abstractmethod
    def handle_message(self, message, address):
        pass

    def inwards_message_mainloop(self):
        while self.running:
            message, address = receive_message(self.message_socket)

            if isinstance(message, MessageConfirmation):
                self.unconfirmed_message_storage.recieve_confirmation(message)
                continue

            if isinstance(message, ReliableMessage):
                self.send_to(MessageConfirmation(message.id), address)

                reliable_message_id_storage = self.get_reliable_message_id_storage(message, address)
                if message.id in reliable_message_id_storage:
                    continue
                else:
                    reliable_message_id_storage.add(message.id)
                    message = message.payload

            self.handle_message(message, address)

    def reliable_message_resend_mainloop(self):
        while self.running:
            for message in self.unconfirmed_message_storage.get_messages():
                now = time()
                if (now - message.last_send_time) > (RELIABLE_MESSAGE_RESEND_DELAY / 1000):
                    self.send_to(message.message, message.address)
                    message.last_send_time = now

            sleep(RESEND_MESSAGE_RESEND_ITERATION_DELAY / 1000)

    def poll_messages(self):
        return self.message_storage.poll()

    def enqueue_message(self, message):
        self.message_storage.add(message)

    def send_to(self, message, address):
        packet = get_packet(message)
        with self.send_lock:
            if 100 * random() > SIMULATED_PACKAGE_LOSS_PERCENTAGE:
                self.message_socket.sendto(packet, address)

    def send_to_reliable(self, message, address):
        reliable_message = ReliableMessage(message)
        self.unconfirmed_message_storage.add_message(reliable_message, address)
        for _ in range(RELIABLE_MESSAGE_INITIAL_SEND_COUNT):
            self.send_to(reliable_message, address)

class CommunicationServer(CommunicationEndpoint):

    def __init__(self, address, start = False):
        self.hosting_client: Optional[HostingCommunicationClient] = None
        self.connected_players: dict[messages.ObjectId, ServerSidePlayerHandle] = {}
        message_storage = ReceivedMessageStorage()

        message_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        message_socket.bind(address)

        super().__init__(message_socket, message_storage, "CommServer")

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
            self.connected_players[player_id] = ServerSidePlayerHandle(player_id, address)

    def send_to_all(self, message):
        for player in self.connected_players.values():
            self.send_to(message, player.address)

        if self.hosting_client != None:
            self.hosting_client.handle_message(message)

    def send_to_all_reliable(self, message):
        for player in self.connected_players.values():
            self.send_to_reliable(message, player.address)

        if self.hosting_client != None:
            self.hosting_client.handle_message(message)

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

    def __init__(self, own_address, server_address, start = False):
        CommunicationClient.__init__(self)
        self.reliable_message_id_storage = ConstSizeQueue(RELIABLE_MESSAGE_ID_STORAGE_SIZE)
        self.server_address = server_address

        message_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        message_socket.bind(own_address)
        CommunicationEndpoint.__init__(self, message_socket, ReceivedMessageStorage(), "InetCommClient")

        if start:
            self.start()

    def get_reliable_message_id_storage(self, message, address) -> ConstSizeQueue:
        return self.reliable_message_id_storage

    def handle_message(self, message, address):
        assert(isinstance(message, messages.MessageToClient))
        self.enqueue_message(message)

    def send(self, message):
        self.send_to(messages.MessageToServerWithId(self.id, message), self.server_address)

    def send_reliable(self, message):
        self.send_to_reliable(messages.MessageToServerWithId(self.id, message), self.server_address)

# on the same machine as server, doesn't need internet
class HostingCommunicationClient(CommunicationClient):

    def __init__(self, server: CommunicationServer):
        super().__init__()
        self.server = server
        self.message_storage = ReceivedMessageStorage()

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

    def __init__(self, player_id: messages.ObjectId, address: tuple[str, int]):
        self.id = player_id
        self.address = address
        self.reliable_message_id_storage = ConstSizeQueue(RELIABLE_MESSAGE_ID_STORAGE_SIZE)
