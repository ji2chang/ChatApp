import json
import socket
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import UDPPortManager
from JSONDatabase import JSONDatabase
from RequestHandler import RequestHandler
from UserUtil import UserManager

class ServerCore:
    def __init__(self, host='127.0.0.1', port=49000, max_workers=10):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((host, port))
        self.db = JSONDatabase()
        self.user_manager = UserManager(self.db)
        self.handler = RequestHandler(self.user_manager,self.db)
        self._shutdown_flag = threading.Event()
        self._thread_pool = ThreadPoolExecutor(max_workers=max_workers)
        self._active_tasks = set()
        self._task_lock = threading.Lock()

    def _server_action(self):
        while not self._shutdown_flag.is_set():
            try:
                self.sock.settimeout(1)
                data, addr = self.sock.recvfrom(1024)

                future = self._thread_pool.submit(self._process_client, data, addr)

                with self._task_lock:
                    self._active_tasks.add(future)
                future.add_done_callback(self._task_completed)
            except socket.timeout:
                continue
            except OSError as e:
                if not self._shutdown_flag.is_set():
                    print(f"Socket error: {e}")
                break

    def _task_completed(self, future):
        with self._task_lock:
            self._active_tasks.discard(future)

    def start(self):
        threading.Thread(target=self._server_action, daemon=True).start()

    def _process_client(self, data: bytes, addr: tuple):
        try:
            # utf-8 e rimuovere BOM
            request = data.decode('utf-8-sig').strip()
            response = self.handler.handle_request(request)
            with UDPPortManager.port_manager.get_free_socket() as sock:
                sock.sendto(response.encode('utf-8'), addr)
        except UnicodeError:
            sock.sendto(
                json.dumps({"status": "error", "reason": "encoding_error"}).encode('utf-8'),
                addr
            )

    def close(self):
        print("[*] Chiudendo il server...")

        # 1. comunicare i thread che il processo principale è chiusa
        self._shutdown_flag.set()

        # 2. chiudere il server socket
        self.sock.close()

        # 3. aspettare un attimo i thread
        start_time = time.time()
        while self._active_tasks and time.time() - start_time < 5:
            time.sleep(0.1)

        # 4. terminare i thread
        with self._task_lock:
            for task in self._active_tasks:
                task.cancel()

        # 5. salvare i dati
        self.db.close()

        print("[✓] Server terminato!")

if __name__ == '__main__':
    server = ServerCore()
    server.start()
    while True:
        command = input("> ")
        if command == "exit":
            server.close()
            break
