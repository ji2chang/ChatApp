import datetime
import hashlib
import multiprocessing
import queue
import secrets
import socket
import threading
import time
from typing import Optional
import server.JSONDatabase as JSONDatabase

import server.Message as Message
import server.UDPPortManager as UDPPortManager
from server.TokenManager import TokenManager


USER_DEFAULT_PORT = 49001

def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

class UserManager:
    def __init__(self, db: JSONDatabase.JSONDatabase, token_manager: TokenManager):
        self.db = db
        self.lock = threading.Lock()
        self.token_manager = token_manager
        self.message_queue = multiprocessing.Queue()
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

    def login(self, username: str, password: str, ip:str, port:int) -> str | None:
        user = self.db.get_user_by_username(username)
        if not user or user["password"] != _hash_password(password):
            return None
        token = secrets.token_hex(16)
        self.token_manager.store_token(token, username,ip,port)
        return token

    def get_user_info(self, username: str) -> Optional[dict]:
        user = self.db.get_user_by_username(username)
        return user.copy()

    def log_message(self, message: Message.Message) -> None:
        self.message_queue.put(message)

    def logout(self,token:str) -> None:
        self.token_manager.delete_token(token)

    def get_friends(self,username:str):
        friends = self.db.get_friends(username)
        return friends

    def _send_messages(self):
        while True:
            temp_queue = queue.Queue()
            while not self.message_queue.empty():
                msg: Message.Message = self.message_queue.get()
                target_username = msg.receiver
                if not self.is_online(target_username):
                    temp_queue.put(msg)
                    continue
                user = self.token_manager.get_user_by_username(target_username)
                if user is None:
                    temp_queue.put(msg)
                    continue
                ip = user["ip"]
                with UDPPortManager.port_manager.get_free_socket() as sock:
                    sock.sendto(msg.to_json().encode('utf-8'), (ip, USER_DEFAULT_PORT))
            time.sleep(5)
            while not temp_queue.empty():
                self.message_queue.put(temp_queue.get())


    def make_friend(self,user1:str,user2:str) -> bool:
        if not self.db.exists(user1) or not self.db.exists(user2):
            return False
        self.db.add_friend(user1,user2)
        self.db.add_friend(user2,user1)
        return True


