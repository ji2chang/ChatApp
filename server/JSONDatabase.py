import datetime
import json
import os
import threading
import time
import uuid
from typing import Dict, Any, Optional


class JSONDatabase:
    def __init__(self, file_path: str = "server/users.json", sync_interval: int = 60):
        self.file_path = file_path
        self._ensure_file_exists()
        self.sync_interval = sync_interval
        self._last_sync = 0
        self._lock = threading.Lock()
        self._load()
        self._ensure_database_format()
        def _daemon():
            while True:
                time.sleep(self.sync_interval)
                self._sync_to_disk()

        threading.Thread(target=_daemon,daemon=True).start()

    def _load(self):
        try:
            with open(self.file_path, 'r') as f:
                self._data = json.load(f)
        except json.JSONDecodeError:
            self._data = {}

    def _ensure_database_format(self):
        if "users" not in self._data:
            self._data["users"] = {}
        if "indexes" not in self._data:
            self._data["indexes"] = {
                "username_to_uid" : {}
            }

    def _ensure_file_exists(self):
        if not os.path.exists(self.file_path):
            with open(self.file_path, 'w') as f:
                json.dump({}, f)

    def _sync_to_disk(self):
        with self._lock:
            with open(self.file_path, 'w') as f:
                json.dump(self._data, f, indent=2) # salvare tutto il file (forse da migliorare?)

    def add_user(self,username:str, value : any):
        uid = str(uuid.uuid4().hex[:8])
        with self._lock:
            self._data["users"][uid] = value
            self._data["indexes"]["username_to_uid"][username] = uid
            self._data["users"][uid]["friends"] = {}
        return uid

    def get_user_by_username(self, username: str) -> Dict[str,Any] | None:
        if not self.exists(username):
            return None
        return self._data["users"][self._data["indexes"]["username_to_uid"][username]]

    def close(self):
        self._sync_to_disk()

    def get_user_by_uid(self, uid: str) -> Dict[str, Any]:
        return self._data["users"].get(uid)

    def update_user_info(self, uid: Optional[str] = None, username: Optional[str] = None, info: Dict[str, Any] = None):
        if uid is None:
            uid = self._data["indexes"]["username_to_uid"].get(username)
        with self._lock:
            self._data["users"][uid] = info

    def get_friends(self, username: str) -> Dict[str, Any]:
        uid = self._data["indexes"]["username_to_uid"].get(username)
        return self._data["users"][uid]["friends"]

    def add_friend(self,username1: str,username2: str):
        uid1 = self._data["indexes"]["username_to_uid"].get(username1)
        with self._lock:
            self._data["users"][uid1]["friends"][username2] = {}

    def exists(self,username: str) -> bool:
        return username in self._data["indexes"]["username_to_uid"]