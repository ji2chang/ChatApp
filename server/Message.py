import json


class Message:
    def __init__(self, message, sender, receiver, date):
        self.message = message
        self.sender = sender
        self.receiver = receiver
        self.date = date

    def __hash__(self):
        return hash((self.message, self.sender, self.receiver, self.date))

    def to_json(self) -> str:
        return json.dumps({"message": self.message, "sender": self.sender, "receiver": self.receiver, "date": self.date})