from cryptography.fernet import Fernet

from pathlib import Path

KEY_FILE = Path.home() / ".teacher_assistant" / ".key"
KEY_FILE.parent.mkdir(exist_ok=True)


def _get_key():
    if not KEY_FILE.exists():
        KEY_FILE.write_bytes(Fernet.generate_key())
    return KEY_FILE.read_bytes()


_fernet = Fernet(_get_key())


def encrypt(text: str) -> str:
    if not text:
        return ""
    return _fernet.encrypt(text.encode()).decode()


def decrypt(text: str) -> str:
    if not text:
        return ""
    return _fernet.decrypt(text.encode()).decode()
