"""Security utilities: password hashing + JWT issuance/verification.

Only the primitives live here. Route-level auth wiring is added in TASK009.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ---------- Password ----------
def hash_password(raw: str) -> str:
    return pwd_context.hash(raw)


def verify_password(raw: str, hashed: str) -> bool:
    """Verify a password against its hash.

    Falls back to direct bcrypt.checkpm() when passlib's CryptContext
    hits the known bcrypt-version incompatibility (``password cannot be
    longer than 72 bytes`` caused by passlib reading ``bcrypt.__about__``
    which was removed in bcrypt >= 4.2).
    """
    try:
        return pwd_context.verify(raw, hashed)
    except Exception:
        # passlib/bcrypt version mismatch — use bcrypt directly
        try:
            import bcrypt
            return bcrypt.checkpw(raw.encode("utf-8"), hashed.encode("utf-8"))
        except Exception:
            return False


# ---------- JWT ----------
def create_access_token(subject: str | int, extra: dict[str, Any] | None = None) -> str:
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any] | None:
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        return None
