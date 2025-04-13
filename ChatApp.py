import json
import socket
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any

import UDPPortManager
import UserUtil

class APIClient:
    def __init__(self, server_ip:str = "127.0.0.1",server_port:int = 49000, max_workers: int = 4):
        self.server_ip = server_ip
        self.server_port = server_port
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self._socket_pool = []
        self._pool_lock = threading.Lock()
        self._token = None
        self._default_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._default_sock.bind(('0.0.0.0', UserUtil.USER_DEFAULT_PORT))
        self._message_receiver = threading.Thread(target=self._receive_message,daemon=True)
        self._message_receiver.start()



    def _send_request(self, request: Dict[str, Any], retry: int = 3) -> Dict[str, Any]:
        with UDPPortManager.port_manager.get_free_socket() as sock:
            raw_data = json.dumps(request).encode('utf-8')
            sock.sendto(raw_data, (self.server_ip, self.server_port))
            while retry > 0:
                try:
                    data, _ = sock.recvfrom(65535)
                    return json.loads(data.decode('utf-8'))
                except socket.timeout:
                    retry -= 1
                    if retry == 0:
                        raise
                    continue
        return {"error":"fail_to_send"}


    def register(self, username: str, password: str, **kwargs) -> Dict[str, Any]:
        request = {
                "action": "register",
                "params": {
                    "username": username,
                    "password": password,
                    **kwargs
                }
            }
        return self._send_request(request)


    def login(self, username: str, password: str) -> Dict[str, Any]:
        request = {
                "action": "login",
                "params": {
                    "username": username,
                    "password": password
                }
            }
        response = self._send_request(request)
        if response["status"] == "success":
            self._token = response["token"]
        return response

    def get_user_info(self, uid: str) -> Dict[str, Any]:
        return self.executor.submit(
            self._send_request,
            {
                "action": "get_info",
                "params": {
                    "uid": uid,
                    "token": self._token
                },

            }
        ).result()

    def logout(self):
        return self.executor.submit(
            self._send_request,
            {
                "action": "logout",
                "params": {
                    "token": self._token
                }
            }
        ).result()

    def close(self):
        self.executor.shutdown()
        with self._pool_lock:
            for sock in self._socket_pool:
                sock.close()

    def chat(self, target_user, message):
        server_request = {
            "action": "chat",
            "params": {
                "target_username": target_user,
                "message": message,
                "token": self._token
            },

        }
        response = self._send_request(server_request,3)
        return response

    def _receive_message(self):
        while True:
            data, _ = self._default_sock.recvfrom(65535)
            parsed_data = json.loads(data.decode('utf-8'))
            print(f"[{parsed_data['date']}] {parsed_data['sender']}: {parsed_data['message']}")

if __name__ == '__main__':
    client = APIClient()
    while True:
        command = input("> ")
        if command == "login":
            username = input("Username: ")
            password = input("Password: ")
            print(client.login(username,password))
        elif command == "chat":
            username = input("Username: ")
            msg = input("Message: ")
            print(client.chat(username,msg))
        elif command == "register":
            username = input("Username: ")
            password = input("Password: ")
            print(client.register(username,password))
        elif command == "logout":
            print(client.logout())