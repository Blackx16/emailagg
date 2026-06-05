from cryptography.fernet import Fernet
from app.core.config import settings

_fernet = Fernet(settings.FERNET_KEY.encode())


def encrypt_token(plain: str) -> str:
    """Encrypt a plain-text OAuth token for storage."""
    return _fernet.encrypt(plain.encode()).decode()


def decrypt_token(encrypted: str) -> str:
    """Decrypt a stored OAuth token."""
    return _fernet.decrypt(encrypted.encode()).decode()
