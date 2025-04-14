import datetime
import json
import os
import socket
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any

from server import UDPPortManager, UserUtil

DEFAULT_SERVER_IP = "192.168.1.104"
class APIClient:
    def __init__(self, server_ip:str = DEFAULT_SERVER_IP,server_port:int = 49000, max_workers: int = 4):
        self.file_path = "user/chats.json"
        self._server_ip = server_ip
        self._server_port = server_port
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self._socket_pool = []
        self._pool_lock = threading.Lock()
        self._default_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._default_sock.bind(('0.0.0.0', UserUtil.USER_DEFAULT_PORT))
        self._message_receiver = threading.Thread(target=self._receive_message,daemon=True)
        self._message_receiver.start()
        self.current_user = {}
        self.friends = {}
        self._chat_lock = threading.Lock()
        self._load_chats()


    def connect_server(self,server_ip:str,server_port:int = 49000):
        self._server_ip = server_ip
        self._server_port = server_port

    def _load_chats(self):
        if not os.path.exists(self.file_path):
            with open(self.file_path, 'w') as f:
                json.dump({}, f)
        try:
            with open(self.file_path, 'r') as f:
                self.chat_history = json.load(f)
        except json.JSONDecodeError:
            self.chat_history = {}

    def save_messages(self):
        with self._chat_lock:
            with open(self.file_path, 'w') as f:
                json.dump(self.chat_history, f, indent=2) # salvare tutto il file (forse da migliorare?)

    def _send_request(self, request: Dict[str, Any], retry: int = 3) -> Dict[str, Any]:
        with UDPPortManager.port_manager.get_free_socket() as sock:
            raw_data = json.dumps(request).encode('utf-8')
            sock.sendto(raw_data, (self._server_ip, self._server_port))
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
            self.current_user["username"] = username
            with self._chat_lock:
                if username not in self.chat_history:
                    self.chat_history[username] = {}
        return response

    def get_friends(self):
        request = {
            "action": "get_friends",
            "params": {
                "token" : self.current_user["token"]
            }
        }
        response = self.executor.submit(
            self._send_request,
            request,
        ).result()
        if response["status"] == "success":
            self.friends = response["friends"]
            for friend in self.friends:
                self.friends[friend] = self.get_user_info(friend)

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
        self.logout()
        self.save_messages()
        self.executor.shutdown()
        with self._pool_lock:
            for sock in self._socket_pool:
                sock.close()

    def chat(self, target_user, message):
        request = {
            "action": "chat",
            "params": {
                "target_username": target_user,
                "message": message,
                "token": self.current_user["token"]
            },
        }
        response = self.executor.submit(
            self._send_request,
            request
        ).result()
        if response["status"] == "success":
            self._add_message(target_user,self.current_user["nickname"], message,datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        return response

    def _add_message(self,dest_user:str,sender:str,message:str,date:str):
        curr_user = self.current_user["username"]
        with self._chat_lock:
            if curr_user not in self.chat_history:
                self.chat_history[curr_user] = {}
            if dest_user not in self.chat_history[curr_user]:
                self.chat_history[curr_user][dest_user] = []
            self.chat_history[curr_user][dest_user].append(f"[{date}] {sender}: {message}")

    def _receive_message(self):
        while True:
            data, _ = self._default_sock.recvfrom(65535)
            parsed_data = json.loads(data.decode('utf-8'))
            self._default_sock.sendto(json.dumps({"status":"success"}).encode('utf-8'), (self._server_ip, self._server_port))
            sender = parsed_data["sender"]
            if sender in self.friends:
                nickname = self.friends[sender]["info"]["nickname"]
            else:
                nickname = self.get_user_info(sender)
                self.friends[sender] = {"info":{"nickname":nickname}}
            self._add_message(sender,nickname,parsed_data["message"],parsed_data["date"])

    def get_messages(self,target_user):
        return self.chat_history[self.current_user["username"]].get(target_user,[])

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