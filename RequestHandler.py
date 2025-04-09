import json
from enum import Enum

from UserUtil import UserManager
from JSONDatabase import JSONDatabase

class ActionType(Enum):
    REGISTER = "register"
    LOGIN = "login"
    GET_INFO = "get_info"


class RequestHandler:
    def __init__(self, user_manager: UserManager, db: JSONDatabase):
        self.user_manager = user_manager
        self.db = db

    def handle_request(self, raw_request: str) -> str | None:
        try:
            request = json.loads(raw_request)
            action = request.get("action")
            params = request.get("params", {})

            # 路由到对应操作
            if action == ActionType.REGISTER.value:
                return self._handle_register(params)
            elif action == ActionType.LOGIN.value:
                return self._handle_login(params)
            elif action == ActionType.GET_INFO.value:
                return self._handle_get_info(params)
        except ValueError as e:
            return json.dumps({"status": "error", "message": "invalid_json"})
        return json.dumps({"status": "error", "message": "action_not_found"})

    def _handle_register(self, params: dict) -> str:
        required = ["username", "password"]
        if not all(k in params for k in required):
            return json.dumps({"status": "error", "message": "missing_field"})

        success = self.user_manager.register(
            params
        )
        if success:
            return json.dumps({"status": "success"})
        else:
            return json.dumps({"status": "error", "message": "register_error"})

    def _handle_login(self, params: dict) -> str:
        required = ["username", "password"]
        if not all(k in params for k in required):
            return json.dumps({"status": "error", "message": "missing_field"})
        if self.user_manager.login(**params):
            return json.dumps({"status": "success"})
        else:
            return json.dumps({"status": "error", "message": "login_failed"})

    def _handle_get_info(self, params: dict) -> str:
        if "username" not in params:
            return json.dumps({"status": "error", "message": "missing_field"})
        info = self.user_manager.get_user_info(params["username"])
        if info:
            return json.dumps({"status": "success", "info": str(info)})
        else:
            return json.dumps({"status": "error", "message": "user_not_found"})