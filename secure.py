from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import pad, unpad
import base64


key = '133BBB3212332231'
key = key.encode('utf8')


def get_cipher(message):
    iv = get_random_bytes(16)
    aes = AES.new(key, AES.MODE_CBC, iv)
    message += ' '*(16 - len(message) % 16)  # add padding
    cipher = aes.encrypt(message.encode("utf8"))
    cipher = base64.b64encode(iv + cipher)
    return cipher


def get_plaintext(cipher):
    decoded_message = base64.b64decode(cipher)
    iv = decoded_message[:16]

    cipher = AES.new(key, AES.MODE_CBC, iv)
    decrypted_message = cipher.decrypt(decoded_message[16:]).strip()
    decrypted_message = decrypted_message.decode('utf8')

    decrypted_message = bytes(decrypted_message, 'utf8').decode('utf8')

    return decrypted_message
