from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
import jwt
from pwdlib import PasswordHash
from pwdlib.hashers.bcrypt import BcryptHasher
from app.core.config import get_settings

# Configure PasswordHash with BcryptHasher
_password_hash = PasswordHash((BcryptHasher(),))


def hash_password(password: str) -> str:
    """Hashes a plaintext password using pwdlib with bcrypt."""
    return _password_hash.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plaintext password against its bcrypt hash."""
    return _password_hash.verify(plain_password, hashed_password)


def create_access_token(subject: str | int, extra_claims: Optional[Dict[str, Any]] = None) -> str:
    """Generates a signed JWT token with expiration."""
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    to_encode: Dict[str, Any] = {"sub": str(subject), "exp": expire}
    if extra_claims:
        to_encode.update(extra_claims)
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> Dict[str, Any]:
    """Decodes and validates a JWT token."""
    settings = get_settings()
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
