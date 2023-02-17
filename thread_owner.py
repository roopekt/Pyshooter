import threading
from abc import ABC

class ThreadOwner(ABC):

    def __init__(self, start_immediately = False):
        self.running = start_immediately
        self.threads: list[threading.Thread] = []

    def add_thread(self, thread: threading.Thread, name: str):
        thread.name = name
        self.threads.append(thread)

        if self.running:
            thread.start()

    def start(self):
        assert(not self.running)
        self.running = True
        
        for thread in self.threads:
            thread.start()

    def stop(self, asyncronous = False):
        assert(self.running)
        self.running = False

        if not asyncronous:
            for thread in self.threads:
                thread.join()
