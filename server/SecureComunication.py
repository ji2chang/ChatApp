from cryptography.fernet import Fernet
from server.SecureComunication import SecureComunication


class SecureComunication:
    def __init__(self):
        # Generate a key for encryption and decryption
        self.key = Fernet.generate_key()
        self.cipher_suite = Fernet(self.key)

    def encrypt_message(self, message: str) -> str:
        # Encrypt the message
        encrypted_message = self.cipher_suite.encrypt(message.encode('utf-8'))
        return encrypted_message.decode('utf-8')

    def decrypt_message(self, encrypted_message: str) -> str:
        # Decrypt the message
        decrypted_message = self.cipher_suite.decrypt(encrypted_message.encode('utf-8'))
        return decrypted_message.decode('utf-8')

    def send_message(self, message: str) -> str:
        # Encrypt the message before sending
        return self.encrypt_message(message)

    def receive_message(self, encrypted_message: str) -> str:
        # Automatically decrypt the message upon receiving
        return self.decrypt_message(encrypted_message)


# Example usage
#secure_comm = SecureCommunication()
#message = "Hello, this is a secure message."

# Encrypt and send the message
#encrypted_message = secure_comm.send_message(message)
#print(f"Encrypted Message: {encrypted_message}")

# Receive and decrypt the message
#decrypted_message = secure_comm.receive_message(encrypted_message)
#print(f"Decrypted Message: {decrypted_message}")

