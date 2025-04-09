import json
import os
import threading
import time
from typing import Dict, Any

class JSONDatabase:
    def __init__(self, file_path: str = "users.json", sync_interval: int = 60):
        self.file_path = file_path
        self._ensure_file_exists()
        self.sync_interval = sync_interval
        self._data = {}
        self._last_sync = 0
        self._lock = threading.Lock()
        self._load()
        threading.Thread(target=self._sync_to_disk(),daemon=True).start()

    def _load(self):
        try:
            with open(self.file_path, 'r') as f:
                self._data = json.load(f)
        except json.JSONDecodeError:
            self._data = {}

    def _ensure_file_exists(self):
        if not os.path.exists(self.file_path):
            with open(self.file_path, 'w') as f:
                json.dump({}, f)

    def _sync_to_disk(self):
        with self._lock:
            time_passed = time.time() - self.sync_interval
            if time_passed >= self.sync_interval:
                with open(self.file_path, 'w') as f:
                    json.dump(self._data, f, indent=2)
                self._last_sync = time.time()

    def set(self,username:str, value : any):
        with self._lock:
            self._data[username] = value

    def get(self, username: str) -> Dict[str, Any]:
        return self._data.get(username)

    def close(self):
        self._sync_to_disk()