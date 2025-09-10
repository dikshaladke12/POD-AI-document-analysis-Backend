import base64
import hashlib
import json
from datetime import datetime, date
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from django.conf import settings
from django.db import models

# class EncryptedBaseField:
#     def get_secret_key(self):
#         return hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest()

#     def encrypt(self, value):
#         if value is None:
#             return value
#         if isinstance(value, (dict, list)):
#             value = json.dumps(value)
#         elif not isinstance(value, str):
#             value = str(value)

#         cipher = AES.new(self.get_secret_key(), AES.MODE_ECB)
#         padded = pad(value.encode("utf-8"), AES.block_size)
#         encrypted = cipher.encrypt(padded)
#         return base64.b64encode(encrypted).decode("utf-8")

#     def decrypt(self, value):
#         if value is None:
#             return value
#         try:
#             if len(value.strip()) % 4 != 0:
#                 raise ValueError("Invalid base64 padding")
#             decoded = base64.b64decode(value)
#             cipher = AES.new(self.get_secret_key(), AES.MODE_ECB)
#             decrypted = cipher.decrypt(decoded)
#             return unpad(decrypted, AES.block_size).decode("utf-8")
#         except Exception:
#             return value

# class EncryptedTextField(models.TextField, EncryptedBaseField):
#     def get_prep_value(self, value):
#         try:
#             base64.b64decode(value)
#             return value
#         except Exception:
#             return self.encrypt(value)

#     def from_db_value(self, value, expression, connection):
#         return self.decrypt(value)

# class EncryptedCharField(models.CharField, EncryptedBaseField):
#     def get_prep_value(self, value):
#         if value is None:
#             return value
#         try:
#             base64.b64decode(value)
#             return value  # already encrypted
#         except Exception:
#             return self.encrypt(value)

#     def from_db_value(self, value, expression, connection):
#         return self.decrypt(value)

#     def to_python(self, value):
#         # Ensure decrypt on access from forms and serializer assignment
#         return self.decrypt(value)

#     def value_from_object(self, obj):
#         # When getting value to be serialized or written
#         return self.decrypt(super().value_from_object(obj))

# class EncryptedJSONField(models.JSONField, EncryptedBaseField):
#     def get_prep_value(self, value):
#         try:
#             base64.b64decode(value)
#             return value
#         except Exception:
#             return self.encrypt(value)

#     def from_db_value(self, value, expression, connection):
#         decrypted = self.decrypt(value)
#         try:
#             return json.loads(decrypted)
#         except Exception:
#             return decrypted

# class EncryptedDateField(models.DateField, EncryptedBaseField):
#     def get_prep_value(self, value):
#         if value in (None, ""):
#             return value
#         try:
#             base64.b64decode(value)
#             return value  # already encrypted
#         except Exception:
#             if isinstance(value, (datetime, date)):
#                 value = value.strftime("%Y-%m-%d")
#             return self.encrypt(value)

#     def from_db_value(self, value, expression, connection):
#         decrypted = self.decrypt(value)
#         try:
#             return datetime.strptime(decrypted, "%Y-%m-%d").date()
#         except Exception:
#             return None

#     def pre_save(self, model_instance, add):
#         raw_value = getattr(model_instance, self.attname)
#         encrypted_value = self.get_prep_value(raw_value)
#         setattr(model_instance, self.attname, encrypted_value)
#         return encrypted_value

class EncryptedBaseField:
    def get_secret_key(self):
        return hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest()

    def is_encrypted(self, value):
        if not isinstance(value, str):
            return False
        try:
            decoded = base64.b64decode(value.encode(), validate=True)
            cipher = AES.new(self.get_secret_key(), AES.MODE_ECB)
            decrypted = cipher.decrypt(decoded)
            unpad(decrypted, AES.block_size)
            return True
        except Exception:
            return False

    def encrypt(self, value):
        if value is None or self.is_encrypted(value):
            return value
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        elif not isinstance(value, str):
            value = str(value)

        cipher = AES.new(self.get_secret_key(), AES.MODE_ECB)
        padded = pad(value.encode("utf-8"), AES.block_size)
        encrypted = cipher.encrypt(padded)
        return base64.b64encode(encrypted).decode("utf-8")

    def decrypt(self, value):
        if value is None:
            return value
        try:
            if len(value.strip()) % 4 != 0:
                raise ValueError("Invalid base64 padding")
            decoded = base64.b64decode(value)
            cipher = AES.new(self.get_secret_key(), AES.MODE_ECB)
            decrypted = cipher.decrypt(decoded)
            return unpad(decrypted, AES.block_size).decode("utf-8")
        except Exception:
            return value


class EncryptedCharField(models.CharField, EncryptedBaseField):
    def get_prep_value(self, value):
        if value is None:
            return value
        return value if self.is_encrypted(value) else self.encrypt(value)

    def from_db_value(self, value, expression, connection):
        return self.decrypt(value)

    def to_python(self, value):
        return self.decrypt(value)

    def value_from_object(self, obj):
        return self.decrypt(super().value_from_object(obj))


class EncryptedTextField(models.TextField, EncryptedBaseField):
    def get_prep_value(self, value):
        if value is None:
            return value
        return value if self.is_encrypted(value) else self.encrypt(value)

    def from_db_value(self, value, expression, connection):
        return self.decrypt(value)

    def to_python(self, value):
        return self.decrypt(value)

    def value_from_object(self, obj):
        return self.decrypt(super().value_from_object(obj))


class EncryptedJSONField(models.JSONField, EncryptedBaseField):
    def get_prep_value(self, value):
        if value is None:
            return value
        return value if self.is_encrypted(value) else self.encrypt(value)

    def from_db_value(self, value, expression, connection):
        decrypted = self.decrypt(value)
        try:
            return json.loads(decrypted)
        except Exception:
            return decrypted


class EncryptedDateField(models.DateField, EncryptedBaseField):
    def get_prep_value(self, value):
        if value in (None, ""):
            return value
        if isinstance(value, (datetime, date)):
            value = value.strftime("%Y-%m-%d")
        return value if self.is_encrypted(value) else self.encrypt(value)

    def from_db_value(self, value, expression, connection):
        decrypted = self.decrypt(value)
        try:
            return datetime.strptime(decrypted, "%Y-%m-%d").date()
        except Exception:
            return None

    def to_python(self, value):
        try:
            return datetime.strptime(self.decrypt(value), "%Y-%m-%d").date()
        except Exception:
            return None

    def pre_save(self, model_instance, add):
        raw_value = getattr(model_instance, self.attname)
        encrypted_value = self.get_prep_value(raw_value)
        setattr(model_instance, self.attname, encrypted_value)
        return encrypted_value
