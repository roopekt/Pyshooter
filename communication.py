import socket
import threading
from thread_owner import ThreadOwner
import pickle
import messages
from random import random
from abc import ABC, abstractmethod
from typing import Optional, Callable
from dataclasses import dataclass, field
from time import time, sleep
from objectid import ObjectId, get_new_object_id
from portforwarding import PortForwarder

RELIABLE_MESSAGE_INITIAL_SEND_COUNT = 2
RELIABLE_MESSAGE_ID_STORAGE_SIZE = 1024
RELIABLE_MESSAGE_RESEND_DELAY = 30 #in milli seconds
RESEND_MESSAGE_RESEND_ITERATION_DELAY = 15

# reliable communication protocol:
# at first, the message (ReliableMessage) is sent multiple times
# if the receiver receives the message, it sends a confirmation (MessageConfirmation)
# the message is resent on regular intervals, until a confirmation is received
# the receiver remembers recently received messages (by id), and only acts on the first message (confirmation is always sent)

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

    def poll(self, filter_predicate: Callable[..., bool]):
        with self.lock:
            output = [m for m in self.messages if filter_predicate(m)]
            self.messages = [m for m in self.messages if m not in output]
            unhandled_count = len(self.messages)

        if unhandled_count > 100:
            print(f"WARNING: {unhandled_count} messages left in buffer.")

        return output
    
    def remove_non_matching(self, filter_predicate: Callable[..., bool]):
        with self.lock:
            self.messages = [m for m in self.messages if filter_predicate(m)]

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
    id: ObjectId = field(init=False)

    def __post_init__(self):
        self.id = get_new_object_id()

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
        self.unconfirmed_messages: dict[ObjectId, UnconfirmedMessage] = {}
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

class HighLevelSocket:

    def __init__(self, low_level_socket: socket.socket):
        self.socket = low_level_socket
        self.send_lock = threading.Lock()

    def send_to(self, message, address):
        packet = pickle.dumps(message)
        with self.send_lock:
            if 100 * random() > SIMULATED_PACKAGE_LOSS_PERCENTAGE:
                self.socket.sendto(packet, address)

    def send_to_reliable(self, message, address, unconfirmed_message_storage: UncofirmedMessageStorage):
        reliable_message = ReliableMessage(message)
        unconfirmed_message_storage.add_message(reliable_message, address)
        for _ in range(RELIABLE_MESSAGE_INITIAL_SEND_COUNT):
            self.send_to(reliable_message, address)

    # returns (data, sender's address)
    def receive_message(self):
        data, address = self.socket.recvfrom(16_384)
        message = pickle.loads(data)
        return message, address

class CommunicationEndpoint(ThreadOwner, ABC):

    def __init__(self, low_level_socket: socket.socket, resend_thread_name: str):
        self.message_socket = low_level_socket
        self.message_storage = ReceivedMessageStorage() # unhandled received messages
        self.unconfirmed_message_storage = UncofirmedMessageStorage() # sent unconfirmed reliable messages
        self.socket = HighLevelSocket(low_level_socket)
 
        ThreadOwner.__init__(self)
        self.add_thread(threading.Thread(target=self.reliable_message_resend_mainloop, daemon=True), resend_thread_name)
        self.send_lock = threading.Lock()

    def handle_reliable_message(self, reliable_message: ReliableMessage, address, received_reliable_message_id_storage: ConstSizeQueue):
        self.socket.send_to(MessageConfirmation(reliable_message.id), address)

        if reliable_message.id in received_reliable_message_id_storage:
            return None
        else:
            received_reliable_message_id_storage.add(reliable_message.id)
            return reliable_message.payload

    def reliable_message_resend_mainloop(self):
        while self.running:
            for message in self.unconfirmed_message_storage.get_messages():
                now = time()
                time_since_last_send = now - message.last_send_time

                if time_since_last_send > (RELIABLE_MESSAGE_RESEND_DELAY / 1000):
                    self.socket.send_to(message.message, message.address)
                    message.last_send_time = now

            sleep(RESEND_MESSAGE_RESEND_ITERATION_DELAY / 1000)

    @abstractmethod
    def poll_messages(self, type_to_poll: type = object) -> list:
        pass

    def enqueue_message(self, message):
        self.message_storage.add(message)

class CommunicationServer(CommunicationEndpoint):

    # if external_address is provided, port forwarding will be set up
    def __init__(self, private_address: tuple[str, int], external_address: Optional[tuple[str, int]] = None, start = False):
        self.private_address = private_address
        self.external_address = external_address

        self.hosting_client: Optional[HostingCommunicationClient] = None
        self.connected_players: dict[ObjectId, ServerSidePlayerHandle] = {}

        message_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        message_socket.bind(private_address)

        super().__init__(message_socket, "comm-server-resend")
        self.add_thread(threading.Thread(target=self.inwards_message_mainloop, daemon=True), "comm-server")

        if self.external_address != None:
            self.add_thread(threading.Thread(target=self.port_forwarding_mainloop), "port-forwarding")

        if start:
            self.start()

    def inwards_message_mainloop(self):
        while self.running:
            message, address = self.socket.receive_message()

            if isinstance(message, MessageConfirmation):
                self.unconfirmed_message_storage.recieve_confirmation(message)
                continue

            if isinstance(message, ReliableMessage):
                message = self.handle_reliable_message(message, address, self.get_reliable_message_id_storage(message, address))
                if message == None:
                    continue

            self.handle_message(message, address)

    def port_forwarding_mainloop(self):
        assert self.external_address != None
        forwarder = PortForwarder(self.private_address[0], self.private_address[1], self.external_address[0], self.external_address[1])

        while self.running:
            forwarder.update()
            sleep(0.1)

    def handle_message(self, message: messages.MessageToServerWithId, address):
        assert(isinstance(message, messages.MessageToServerWithId))
        self.add_player_if_new(message.sender_id, address)
        self.enqueue_message(message)

    def get_reliable_message_id_storage(self, message, address):
        player_id = message.payload.sender_id
        self.add_player_if_new(player_id, address)
        return self.connected_players[player_id].reliable_message_id_storage

    def add_player_if_new(self, player_id: messages.ObjectId, address):
        known_ids = list(self.connected_players.keys())
        if self.hosting_client != None:
            known_ids.append(self.hosting_client.id)

        if player_id not in known_ids:
            self.connected_players[player_id] = ServerSidePlayerHandle(player_id, address)

    def send_to_all(self, message):
        for player in self.connected_players.values():
            self.socket.send_to(message, player.address)

        if self.hosting_client != None:
            self.hosting_client.handle_message(message)

    def send_to_all_reliable(self, message):
        for player in list(self.connected_players.values()):
            self.socket.send_to_reliable(message, player.address, self.unconfirmed_message_storage)

        if self.hosting_client != None:
            self.hosting_client.handle_message(message)

    def send_to(self, message, player_id: ObjectId):
        if self.hosting_client != None and self.hosting_client.id == player_id:
            self.hosting_client.handle_message(message)
            return
        
        client = self.connected_players[player_id]
        self.socket.send_to(message, client.address)

    def send_reliable_to(self, message, player_id: ObjectId):
        if self.hosting_client != None and self.hosting_client.id == player_id:
            self.hosting_client.handle_message(message)
            return
        
        client = self.connected_players[player_id]
        self.socket.send_to_reliable(message, client.address, self.unconfirmed_message_storage)

    def poll_messages(self, type_to_poll: type = object) -> list[messages.MessageToServerWithId]:
        return self.message_storage.poll(lambda message: isinstance(message.payload, type_to_poll))
    
    def remove_messages_of_other_types(self, valid_type: type = object):
        self.message_storage.remove_non_matching(lambda message: isinstance(message.payload, valid_type))

class CommunicationClient(ABC):

    def __init__(self):
        self.id = get_new_object_id()

    @abstractmethod
    def send(self, message):
        pass

    @abstractmethod
    def send_reliable(self, message):
        pass

    @abstractmethod
    def poll_messages(self, type_to_poll: type = object) -> list[messages.MessageToClient]:
        pass

    @abstractmethod
    def remove_messages_of_other_types(self, valid_type: type = object):
        pass

class InternetCommunicationClient(CommunicationEndpoint, CommunicationClient):

    def __init__(self, own_address, server_address, start = False):
        CommunicationClient.__init__(self)
        self.reliable_message_id_storage = ConstSizeQueue(RELIABLE_MESSAGE_ID_STORAGE_SIZE) #ids of received reliable messages
        self.server_address = server_address

        message_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        message_socket.bind(own_address)
        CommunicationEndpoint.__init__(self, message_socket, "inet-comm-client-resend")
        self.add_thread(threading.Thread(target=self.inwards_message_mainloop, daemon=True), "inet-comm-client")

        if start:
            self.start()

    def inwards_message_mainloop(self):
        while self.running:
            message, address = self.socket.receive_message()

            if isinstance(message, MessageConfirmation):
                self.unconfirmed_message_storage.recieve_confirmation(message)
                continue

            if isinstance(message, ReliableMessage):
                message = self.handle_reliable_message(message, address, self.reliable_message_id_storage)
                if message == None:
                    continue

            assert(isinstance(message, messages.MessageToClient))
            self.enqueue_message(message)

    def send(self, message):
        self.socket.send_to(messages.MessageToServerWithId(self.id, message), self.server_address)

    def send_reliable(self, message):
        self.socket.send_to_reliable(messages.MessageToServerWithId(self.id, message), self.server_address, self.unconfirmed_message_storage)

    def poll_messages(self, type_to_poll: type = object) -> list:
        return self.message_storage.poll(lambda message: isinstance(message, type_to_poll))

    def remove_messages_of_other_types(self, valid_type: type = object):
        self.message_storage.remove_non_matching(lambda message: isinstance(message, valid_type))

# on the same machine as server, doesn't need internet
class HostingCommunicationClient(CommunicationClient):

    def __init__(self, server: CommunicationServer):
        CommunicationClient.__init__(self)
        self.server = server
        self.message_storage = ReceivedMessageStorage()

    def handle_message(self, message: messages.MessageToClient):
        self.message_storage.add(message)

    def send(self, message):
        message = messages.MessageToServerWithId(self.id, message)
        self.server.handle_message(message, ("direct", 0))

    def send_reliable(self, message):
        self.send(message)

    def poll_messages(self, type_to_poll: type = object) -> list:
        return self.message_storage.poll(lambda message: isinstance(message, type_to_poll))
    
    def remove_messages_of_other_types(self, valid_type: type = object):
        self.message_storage.remove_non_matching(lambda message: isinstance(message, valid_type))

class ServerSidePlayerHandle:

    def __init__(self, player_id: messages.ObjectId, address: tuple[str, int]):
        self.id = player_id
        self.address = address
        self.reliable_message_id_storage = ConstSizeQueue(RELIABLE_MESSAGE_ID_STORAGE_SIZE)
