import hashlib
import json
from typing import Optional
import JSONDatabase
import uuid


def _hash_password(password: str) -> str:
    """密码哈希处理"""
    return hashlib.sha256(password.encode()).hexdigest()


class UserManager:
    def __init__(self, db: JSONDatabase.JSONDatabase):
        self.db = db

    def register(self, params) -> bool:
        params["password"] = _hash_password(params["password"])
        try:
            if self.db.get(params["username"]):
                return False
            self.db.set(params["username"], params)
        except ValueError as e:
            return False
        return True

    def login(self, username: str, password: str) -> bool:
        user = self.db.get(username)
        if not user:
            return False
        return user["password_hash"] == _hash_password(password)

    def get_user_info(self, username: str) -> Optional[dict]:
        return self.db.get(username)
