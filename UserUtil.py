import datetime
import hashlib
import json
import secrets
import threading
import time
from typing import Optional, Any
import JSONDatabase
import uuid


def _hash_password(password: str) -> str:
    """密码哈希处理"""
    return hashlib.sha256(password.encode()).hexdigest()


class UserManager:
    def __init__(self, db: JSONDatabase.JSONDatabase, session_expire_time:int = 3600):
        self.user_sessions = {} # token -> {uid:UID_3213,timestamp:123213,username:name}
        self.session_expire_time = session_expire_time # in secondi
        self.db = db
        self.lock = threading.Lock()
        def _daemon():
            while True:
                time.sleep(300)
                self.clear_expired_tokens()

        self.token_cleaner = threading.Thread(target=_daemon, daemon=True)
        self.token_cleaner.start()

    def register(self, params) -> bool:
        params["password"] = _hash_password(params["password"])
        try:
            if self.db.get_user_by_username(params["username"]):
                return False
            params["info"] = {}
            params["info"]["register_date"] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.db.add_user(params["username"], params)
        except ValueError:
            return False
        return True

    def login(self, username: str, password: str) -> str | None:
        user = self.db.get_user_by_username(username)
        if not user or user["password"] != _hash_password(password):
            return None
        token = secrets.token_hex(16)
        self.store_token(token, username)
        return token

    def get_user_info(self, username: str) -> Optional[dict]:
        return self.db.get_user_by_username(username)

    def is_token_valid(self,token:str):
        with self.lock:
            token_data = self.user_sessions.get(token)
            if token_data is None:
                return False
            return datetime.datetime.now().timestamp() - token_data["timestamp"] > self.session_expire_time

    def get_username_by_token(self, token: str) -> dict[str, Any] | None:
        if not self.is_token_valid(token):
            return None
        return self.user_sessions[token]["username"]

    def clear_expired_tokens(self):
        with self.lock:
            current_time = datetime.datetime.now().timestamp()
            self.user_sessions = {
                token:data
                for token, data in self.user_sessions.items()
                if current_time - data["timestamp"] < self.session_expire_time
            }

    def delete_token(self,token:str):
        self.user_sessions.pop(token)

    def store_token(self, token: str, username: str) -> dict[str, Any] | None:
        self.user_sessions[token] = {"username": username, "timestamp": datetime.datetime.now().timestamp()}

    def flush_token(self,token:str) -> None:
        self.user_sessions[token]["timestamp"] = datetime.datetime.now().timestamp()