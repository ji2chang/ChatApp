import datetime
import json
from concurrent.futures import ThreadPoolExecutor
from enum import Enum
import secrets
from typing import Tuple, Any

import Message
import UDPPortManager
from TokenManager import TokenManager
from UserUtil import UserManager
from JSONDatabase import JSONDatabase

class ActionType(Enum):
    REGISTER = "register"
    LOGIN = "login"
    GET_INFO = "get_info"
    CHAT = "chat"
    LOGOUT = "logout"
    GET_FRIENDS = "get_friends"
    ADD_FRIEND ="add_friend"

class RequestHandler:
    def __init__(self, db: JSONDatabase):
        self.db = db
        self.token_manager = TokenManager()
        self.user_manager = UserManager(self.db,self.token_manager)

    def handle_request(self, raw_request: str, addr:Tuple[str,int]) -> str | None:
        try:
            request = json.loads(raw_request)
            action = request.get("action")
            params = request.get("params")
            if action == ActionType.REGISTER.value:
                return self._handle_register(params)

            params["ip"] = addr[0]
            params["port"] = addr[1]

            if action == ActionType.LOGIN.value:
                return self._handle_login(params)

            if not self.token_manager.is_token_valid(params.get("token")):
                return json.dumps({"status": "error", "message": "Invalid token"})

            if action == ActionType.GET_INFO.value:
                return self._handle_get_info(params)
            elif action == ActionType.CHAT.value:
                return self._handle_chat(params)
            elif action == ActionType.LOGOUT.value:
                return self._handle_logout(params)
            elif action == ActionType.GET_FRIENDS.value:
                return self._handle_get_friends(params)
            elif action == ActionType.ADD_FRIEND.value:
                return self._handle_add_friend(params)
        except ValueError as e:
            return json.dumps({"status": "error", "message": "invalid_json"})
        return json.dumps({"status": "error", "message": "action_not_found"})

    def _handle_register(self, params: dict) -> str:
        required = ["username", "password","info"]
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
        required = ["username", "password","ip"]
        filtered_params = {k: params[k] for k in required if k in params}
        token = self.user_manager.login(**filtered_params)
        if token:
            response = json.loads(self._handle_get_info({"username" : filtered_params["username"]}))

            response["info"]["token"] = token
            return json.dumps(response)
        else:
            return json.dumps({"status": "error", "message": "login_failed"})

    def _handle_get_info(self, params: dict) -> str:
        param_filter = ["username","info"]
        if "username" not in params:
            return json.dumps({"status": "error", "message": "missing_field"})
        info = self.user_manager.get_user_info(params["username"])
        if info:
            response = {key: info[key] for key in param_filter if key in info}
            response["info"]["online"] = self.user_manager.is_online(params["username"])
            response["status"] = "success"
            return json.dumps(response)
        else:
            return json.dumps({"status": "error", "message": "user_not_found"})

    def _handle_chat(self, params: dict) -> str:
        required = ["target_username","message"]
        if not all(k in params for k in required):
            return json.dumps({"status": "error", "message": "missing_field"})
        # loggare questo tentativo
        source_user = self.token_manager.get_user_by_token(params["token"]).get("username")
        target_user = params["target_username"]
        date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        message = Message.Message(sender=source_user,receiver=target_user,message=params["message"],date=date)
        self.user_manager.log_message(message)
        return json.dumps({"status": "success"})

    def _handle_logout(self, params: dict) -> str:
        self.user_manager.logout(params["token"])
        return json.dumps({"status": "success"})

    def _handle_get_friends(self,params:dict) -> str:
        username = self.token_manager.get_user_by_token(params["token"])["username"]
        response = {"status": "success", "friends": self.user_manager.get_friends(username)}
        return json.dumps(response)

    def _handle_add_friend(self,params:dict) -> str:
        required = ["target_username"]
        if not all(k in params for k in required):
            return json.dumps({"status": "error", "message": "missing_field"})
        source_user = self.token_manager.get_user_by_token(params["token"]).get("username")
        target_user = params["target_username"]
        if self.user_manager.make_friend(source_user,target_user):
            return json.dumps({"status": "success"})
        return json.dumps({"status": "error", "message": "user do not exists"})
