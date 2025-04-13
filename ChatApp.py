import json
import socket
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any

import UDPPortManager
import UserUtil
DEFAULT_SERVER_IP = "10.11.214.213"
class APIClient:
    def __init__(self, server_ip:str = DEFAULT_SERVER_IP,server_port:int = 49000, max_workers: int = 4):
        self.server_ip = server_ip
        self.server_port = server_port
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self._socket_pool = []
        self._pool_lock = threading.Lock()
        self._default_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._default_sock.bind(('0.0.0.0', UserUtil.USER_DEFAULT_PORT))
        self._message_receiver = threading.Thread(target=self._receive_message,daemon=True)
        self._message_receiver.start()
        self.current_user = {}
        self.friends = []

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


    def register(self, username: str, password: str, info:dict) -> Dict[str, Any]:
        request = {
                "action": "register",
                "params": {
                    "username": username,
                    "password": password,
                }
            }
        request["params"]["info"] = info
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
            self.current_user = response["info"]
        return response

    def get_friends(self):
        request = {
            "action": "get_friends",
            "params": {
                "token" : self.current_user["token"]
            }
        }
        response = self._send_request(request)
        if response["status"] == "success":
            self.friends = response["friends"]
            for friend in self.friends:
                self.friends[friend] = self.get_user_info(friend)
        else:
            self.friends = []

    def get_user_info(self, username: str) -> Dict[str, Any]:
        return self.executor.submit(
            self._send_request,
            {
                "action": "get_info",
                "params": {
                    "username": username,
                    "token": self.current_user["token"]
                },

            }
        ).result()

    def logout(self):
        return self.executor.submit(
            self._send_request,
            {
                "action": "logout",
                "params": {
                    "token": self.current_user["token"]
                }
            }
        ).result()

    def add_friend(self,username):
        request = {
            "action": "add_friend",
            "params": {
                "target_username" : username,
                "token": self.current_user["token"]
            }
        }
        return self.executor.submit(
            self._send_request,
            request
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
                "token": self.current_user["token"]
            },

        }
        response = self._send_request(server_request,3)
        return response

    def _receive_message(self):
        while True:
            data, _ = self._default_sock.recvfrom(65535)
            parsed_data = json.loads(data.decode('utf-8'))
            self._default_sock.sendto(json.dumps({"status":"success"}).encode('utf-8'), (self.server_ip, self.server_port))
            print(f"[{parsed_data['date']}] {parsed_data['sender']}: {parsed_data['message']}")

if __name__ == '__main__':
    server_ip=input("Inserire ip server: ")
    client = APIClient(server_ip=server_ip)
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
            nickname = input("Nickname: ")
            print(client.register(username,password,{"nickname":nickname}))
        elif command == "logout":
            print(client.logout())