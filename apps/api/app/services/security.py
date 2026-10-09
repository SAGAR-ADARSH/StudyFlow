import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta

import jwt
from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError
from pwdlib.hashers.argon2 import Argon2Hasher
from pwdlib.hashers.bcrypt import BcryptHasher

from app.core.config import get_settings

# New credentials use Argon2id; BcryptHasher remains available so existing accounts can
# authenticate and be upgraded automatically on their next successful login.
_password_hash = PasswordHash((Argon2Hasher(), BcryptHasher()))


def hash_password(password: str) -> str:
    """Hash a password with Argon2id."""
    return _password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    """Verify Argon2id and legacy bcrypt password hashes."""
    try:
        return _password_hash.verify(password, hashed_password)
    except (UnknownHashError, TypeError, ValueError):
        # A malformed or unsupported stored hash should fail authentication, not 500.
        return False


def verify_password_and_update(password: str, hashed_password: str) -> tuple[bool, str | None]:
    """Verify a hash and return a replacement hash when its algorithm needs upgrading."""
    try:
        return _password_hash.verify_and_update(password, hashed_password)
    except (UnknownHashError, TypeError, ValueError):
        return False, None


def _password_signature(password_hash: str) -> str:
    settings = get_settings()
    return hmac.new(
        settings.jwt_secret_key.encode("utf-8"),
        password_hash.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def access_token_matches_password(token_signature: object, password_hash: str) -> bool:
    """Return false for tokens issued before the current password hash was set."""
    if not isinstance(token_signature, str):
        return False
    return hmac.compare_digest(token_signature, _password_signature(password_hash))


def create_access_token(subject: str | int, password_hash: str) -> str:
    """Create a short-lived, issuer-bound JWT invalidated by any password change."""
    settings = get_settings()
    now = datetime.now(UTC)
    issued_at = int(now.timestamp())
    expires_at = int((now + timedelta(minutes=settings.access_token_expire_minutes)).timestamp())
    claims = {
        "sub": str(subject),
        "iss": settings.jwt_issuer,
        "iat": issued_at,
        "exp": expires_at,
        "jti": secrets.token_urlsafe(18),
        "pwd_sig": _password_signature(password_hash),
    }
    return jwt.encode(claims, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, object]:
    """Decode and validate the signature and required access-token claims."""
    settings = get_settings()
    claims = jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
        issuer=settings.jwt_issuer,
        options={"require": ["exp", "iat", "iss", "sub", "jti", "pwd_sig"]},
    )
    if not isinstance(claims.get("sub"), str) or not claims["sub"].isdigit():
        raise jwt.InvalidTokenError("Invalid subject")
    if not isinstance(claims.get("jti"), str) or not claims["jti"]:
        raise jwt.InvalidTokenError("Invalid token identifier")
    return claims
