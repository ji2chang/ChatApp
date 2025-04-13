import datetime
import hashlib
import multiprocessing
import secrets
import socket
import threading
from typing import Optional, Any, is_protocol
import JSONDatabase

import Message
import UDPPortManager
from TokenManager import TokenManager


USER_DEFAULT_PORT = 49001

def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

class UserManager:
    def __init__(self, db: JSONDatabase.JSONDatabase, token_manager: TokenManager):
        self.db = db
        self.lock = threading.Lock()
        self.token_manager = token_manager
        self.message_queue = {}
        self._message_sender = threading.Thread(target=self._send_messages, daemon=True)
        self._message_sender.start()

    def register(self, params) -> bool:
        params["password"] = _hash_password(params["password"])
        try:
            if self.db.get_user_by_username(params["username"]):
                return False
            params["info"]["register_date"] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.db.add_user(params["username"], params)
        except ValueError:
            return False
        return True

    def is_online(self,username:str) -> bool:
        return self.token_manager.get_user_by_username(username) is not None

    def login(self, username: str, password: str, ip:str) -> str | None:
        user = self.db.get_user_by_username(username)
        if not user or user["password"] != _hash_password(password):
            return None
        token = secrets.token_hex(16)
        self.token_manager.store_token(token, username,ip)
        return token

    def get_user_info(self, username: str) -> Optional[dict]:
        user = self.db.get_user_by_username(username)
        return user

    def log_message(self,message:Message.Message) -> None:
        target_username = message.receiver
        if target_username not in self.message_queue:
            self.message_queue[target_username] = multiprocessing.Queue()
        self.message_queue[target_username].put(message)

    def logout(self,token:str) -> None:
        self.token_manager.delete_token(token)

    def send_all_messages(self,target_username:str):
        messages = self.message_queue.get(target_username,multiprocessing.Queue())
        not_sent = multiprocessing.Queue()
        while (not messages.empty()) and self.is_online(target_username):
            ip = self.token_manager.get_user_by_username(target_username)["ip"]
            message = messages.get()
            retry = 3
            with UDPPortManager.port_manager.get_free_socket() as sock:
                sock.sendto(message.to_json().encode('utf-8'), (ip, USER_DEFAULT_PORT))
                while retry > 0:
                    try:
                        data, _ = sock.recvfrom(4096)
                        break
                    except socket.timeout:
                        retry -= 1
                        if retry == 0:
                            not_sent.put(message)
                            break
                        continue
            if messages.empty():
                messages = not_sent
        while not messages.empty():
            self.log_message(messages.get())

    def get_friends(self,username:str):
        friends = self.db.get_friends(username)
        return friends

    def _send_messages(self):
        while True:
            for target_username in self.message_queue.keys():
                self.send_all_messages(target_username)

    def make_friend(self,user1:str,user2:str) -> bool:
        if not self.db.exists(user1) or not self.db.exists(user2):
            return False
        self.db.add_friend(user1,user2)
        self.db.add_friend(user2,user1)
        return True


