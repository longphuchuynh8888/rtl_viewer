# utils/crypto.py
"""Mã hóa / giải mã mật khẩu bằng Fernet (AES)"""

import os
from cryptography.fernet import Fernet

KEY_FILE = "secret.key"

def get_or_create_key() -> bytes:
    if os.path.exists(KEY_FILE):
        with open(KEY_FILE, "rb") as f:
            return f.read()
    key = Fernet.generate_key()
    with open(KEY_FILE, "wb") as f:
        f.write(key)
    return key

_fernet = Fernet(get_or_create_key())

def encrypt_text(text: str) -> str:
    if not text:
        return ""
    return _fernet.encrypt(text.encode()).decode()

def decrypt_text(token: str) -> str:
    if not token:
        return ""
    try:
        return _fernet.decrypt(token.encode()).decode()
    except Exception:
        return ""