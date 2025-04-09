
import threading
from contextlib import contextmanager
import socket

class UDPPortManager:
    def __init__(self):
        self._lock = threading.Lock()
        self._used_ports = set()

    @contextmanager
    def get_free_socket(self):
        sock = None
        try:
            with self._lock:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.bind(('0.0.0.0', 0))
                port = sock.getsockname()[1]
                while port in self._used_ports:
                    sock.close()
                    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    sock.bind(('0.0.0.0', 0))
                    port = sock.getsockname()[1]
                self._used_ports.add(port)

            yield sock
        finally:
            if sock:
                with self._lock:
                    sock.close()
                    self._used_ports.discard(port)

port_manager = UDPPortManager()