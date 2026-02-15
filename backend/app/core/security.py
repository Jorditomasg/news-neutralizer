"""Security utilities: API key encryption/decryption."""

from cryptography.fernet import Fernet, InvalidToken
import structlog

from app.config import settings

logger = structlog.get_logger()

_fernet: Fernet | None = None


def _get_fernet() -> Fernet:
    """Lazy-initialize Fernet cipher with the configured key."""
    global _fernet
    if _fernet is None:
        try:
            _fernet = Fernet(settings.encryption_key.encode())
        except Exception as e:
            logger.error("Invalid ENCRYPTION_KEY — cannot encrypt/decrypt API keys", error=str(e))
            raise ValueError("Invalid ENCRYPTION_KEY configuration") from e
    return _fernet


def encrypt_api_key(plaintext_key: str) -> str:
    """Encrypt an API key for storage in the database."""
    return _get_fernet().encrypt(plaintext_key.encode()).decode()


def decrypt_api_key(encrypted_key: str) -> str:
    """Decrypt an API key from the database. Returns plaintext only in RAM."""
    try:
        return _get_fernet().decrypt(encrypted_key.encode()).decode()
    except InvalidToken:
        logger.error("Failed to decrypt API key — possible key rotation issue")
        raise ValueError("Cannot decrypt API key — encryption key may have changed")
