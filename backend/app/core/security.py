"""Security utilities: API key encryption/decryption."""

from cryptography.fernet import Fernet, InvalidToken
import structlog
import socket
import ipaddress
import jwt
from datetime import datetime, timedelta, timezone
from typing import Any

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

# ── JWT Authentication ────────────────────────────────────────────────────────

ALGORITHM = "HS256"

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Create a new JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and verify a JWT token. Raises jwt.PyJWTError on failure."""
    return jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])

# ── SSRF Prevention ──────────────────────────────────────────────────────────

async def validate_url_for_ssrf(url: str) -> bool:
    """
    Validate that a URL does not resolve to a local/private IP address.
    Raises ValueError if it's considered an SSRF risk.
    """
    from urllib.parse import urlparse
    import asyncio
    
    parsed = urlparse(url)
    hostname = parsed.hostname
    if not hostname:
        raise ValueError("Invalid URL: Missing hostname")

    # Fast-fail for obvious bad hostnames
    if hostname in ["localhost", "127.0.0.1", "[::1]", "0.0.0.0"]:
        raise ValueError(f"SSRF Risk: URL resolves to internal host {hostname}")

    try:
        loop = asyncio.get_running_loop()
        # Resolve hostname to IPs using thread pool to avoid blocking async event loop
        info = await loop.run_in_executor(None, socket.getaddrinfo, hostname, parsed.port or 80)
        
        for result in info:
            ip_str = result[4][0]
            ip_obj = ipaddress.ip_address(ip_str)
            if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local or ip_obj.is_multicast or ip_obj.is_reserved:
                raise ValueError(f"SSRF Risk: URL {url} resolves to private/internal IP {ip_str}")
                
        return True
    except socket.gaierror:
        # If it doesn't resolve here, it might fail later in httpx, which is fine.
        # But if it's an obfuscated internal IP, it might bypass getaddrinfo? 
        # ipaddress.ip_address() handles many integer/hex formats if passed directly.
        try:
            ip_obj = ipaddress.ip_address(hostname)
            if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local or ip_obj.is_multicast or ip_obj.is_reserved:
                raise ValueError(f"SSRF Risk: URL {url} resolves to private/internal IP {hostname}")
        except ValueError:
            pass # Not a direct IP string
            
        return True
