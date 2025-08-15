from nacl import secret, utils
from nacl.encoding import Base64Encoder

# Generate a key (for demo only; in real ZK, users have their own key)
key = utils.random(secret.SecretBox.KEY_SIZE)
box = secret.SecretBox(key)

def encrypt_data(data: str) -> str:
    encrypted = box.encrypt(data.encode(), encoder=Base64Encoder)
    return encrypted.decode()

def decrypt_data(encrypted_data: str) -> str:
    decrypted = box.decrypt(encrypted_data.encode(), encoder=Base64Encoder)
    return decrypted.decode()
