"""Security utilities: API key encryption/decryption."""

from cryptography.fernet import Fernet, InvalidToken
import structlog

from app.config import settings

logger = structlog.get_logger()

_fernet: Fernet | None = None


def _get_fernet() -> Fernet:
    """Lazy-initialize Fernet cipher with the configured key. Auto-generates if missing/invalid."""
    global _fernet
    if _fernet is None:
        try:
            # First try with the currently configured key
            _fernet = Fernet(settings.encryption_key.encode())
        except Exception as e:
            logger.warning("Invalid or missing ENCRYPTION_KEY — generating a new one automatically", error=str(e))
            
            # Generate a new key
            new_key = Fernet.generate_key().decode()
            
            # Save it to .env
            import os
            env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")
            try:
                with open(env_path, "a") as f:
                    f.write(f"\nENCRYPTION_KEY={new_key}\n")
                logger.info("New ENCRYPTION_KEY appended to .env file")
            except Exception as write_err:
                logger.error("Failed to write new ENCRYPTION_KEY to .env", error=str(write_err))
                # Fallback to in-memory only (will be lost on restart, but won't crash now)
                
            # Update settings and initialize Fernet
            settings.encryption_key = new_key
            _fernet = Fernet(new_key.encode())
            
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
