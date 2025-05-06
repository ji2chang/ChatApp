from server.SecureComunication import SecureComunication
import json

class Message:
    def __init__(self, message, sender, receiver, date):
        self.secure_com = SecureComunication()
        self.message = message
        self.encrypted_message = self.secure_com.encrypt_message(message)
        self.sender = sender
        self.receiver = receiver
        self.date = date

    def decrypt_message(self) -> str:
        """
        Decrypts the encrypted message.
        :return: The plaintext message.
        """
        return self.secure_com.decrypt_message(self.encrypted_message)

    def to_json(self) -> str:
        return json.dumps({
            "message": self.encrypted_message,
            "sender": self.sender,
            "receiver": self.receiver,
            "date": self.date
        })