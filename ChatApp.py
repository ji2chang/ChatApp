import json
import socket
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any

import UDPPortManager

class APIClient:
    def __init__(self, server_ip:str = "127.0.0.1",server_port:int = 49000, max_workers: int = 4):
        self.server_ip = server_ip
        self.server_port = server_port
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self._socket_pool = []
        self._pool_lock = threading.Lock()

    def _send_request(self, request: Dict[str, Any], retry: int = 3) -> Dict[str, Any]:
        """核心请求方法（带重试机制）"""
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
        return self.executor.submit(
            self._send_request,
            {
                "action": "register",
                "params": {
                    "username": username,
                    "password": password,
                    **kwargs
                }
            }
        ).result()

    def login(self, username: str, password: str) -> Dict[str, Any]:
        return self.executor.submit(
            self._send_request,
            {
                "action": "login",
                "params": {
                    "username": username,
                    "password": password
                }
            }
        ).result()

    def get_user_info(self, uid: str) -> Dict[str, Any]:
        return self.executor.submit(
            self._send_request,
            {
                "action": "get_info",
                "params": {
                    "uid": uid
                }
            }
        ).result()

    def close(self):
        self.executor.shutdown()
        with self._pool_lock:
            for sock in self._socket_pool:
                sock.close()

if __name__ == '__main__':
    client = APIClient()
    client.register("test", "123")