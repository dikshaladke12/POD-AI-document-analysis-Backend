import base64
import os

key = os.urandom(32)
print("Raw:", key)
print("Base64:", base64.urlsafe_b64encode(key).decode())