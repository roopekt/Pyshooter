import socket
import threading

PORT = 29801
PUBLIC_SERVER_IP = "127.0.0.1" #"195.148.39.50"
LOCAL_SERVER_IP = "10.90.77.3"
BUFFER_SIZE = 4096

class CommunicationServer:

    def __init__(self):
        self.tcp_thread = None

        self.tcp_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
        self.tcp_socket.bind(('', PORT))

        # self.udp_socket = socket.socket(family=socket.AF_INET6, type=socket.SOCK_DGRAM)
        # self.udp_socket.bind(("", 4242))

    def tcp_mainloop(self):
        self.should_run = True
        with self.tcp_socket as tcp_socket:
            tcp_socket.listen()

            while self.should_run:
                connection, address = tcp_socket.accept()
                with connection:
                    data = connection.recv(BUFFER_SIZE).decode("utf-8")
                    print(f"{address}: {data}")
                    connection.send(b"OK")

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
        self.tcp_socket.connect((PUBLIC_SERVER_IP, PORT))

    def send(self, data):
        self.tcp_socket.send(data)
        response = self.tcp_socket.recv(BUFFER_SIZE).decode("utf-8")
        print(f"response received: {response}")
