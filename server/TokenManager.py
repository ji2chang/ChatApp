import datetime
import threading
import time
from typing import Any


class TokenManager:
    def __init__(self,token_expire_time:int = 3600):
        self.tokens = {} # token -> {uid:UID_3213,timestamp:123213,username:name}
        self.lock = threading.Lock()
        def _daemon():
            while True:
                time.sleep(300)
                self.clear_expired_tokens()

        self.token_expire_time = token_expire_time
        self.token_cleaner = threading.Thread(target=_daemon, daemon=True)
        self.token_cleaner.start()
        self.username_to_token = {}
    
    def is_token_valid(self,token:str):
        if not token in self.tokens:
            return False
        return datetime.datetime.now().timestamp() - self.tokens[token]["timestamp"] < self.token_expire_time

    def get_user_by_username(self,username:str):
        return self.get_user_by_token(self.username_to_token.get(username))

    def get_user_by_token(self, token: str) -> dict[str, Any] | None:
        if not self.is_token_valid(token):
            return None
        return self.tokens[token]

    def clear_expired_tokens(self):
        with self.lock:
            valid_tokens = {
                token: data
                for token, data in self.tokens.items()
                if self.is_token_valid(token)
            }

            self.tokens = valid_tokens

            self.username_to_token = {
                data["username"]: token
                for token, data in valid_tokens.items()
            }

    def delete_token(self,token:str):
        with self.lock:
            username = self.get_user_by_token(token)["username"]
            self.tokens.pop(token,None)
            self.username_to_token.pop(username,None)

    def store_token(self, token: str, username: str, ip):
        with self.lock:
            self.tokens[token] = {"username": username, "timestamp": datetime.datetime.now().timestamp(), "ip": ip}
            self.username_to_token[username] = token

    def flush_token(self,token:str) -> None:
        with self.lock:
            self.tokens[token]["timestamp"] = datetime.datetime.now().timestamp()
            self.username_to_token[self.get_user_by_token(token)["username"]] = token

    def get_token_by_username(self, username:str) -> str | None:
        return self.username_to_token.get(username,None)