"""Password hashing and JWT helpers."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
import jwt

from app.core.config import Settings
from app.core.exceptions import AuthenticationError


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8")[:72], bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8")[:72], hashed.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(
    subject: str, settings: Settings, extra: dict[str, Any] | None = None
) -> tuple[str, int]:
    expires_in = settings.access_token_expire_minutes * 60
    now = datetime.now(UTC)
    payload = {"sub": subject, "iat": now, "exp": now + timedelta(seconds=expires_in), **(extra or {})}
    token = jwt.encode(payload, settings.secret_key.get_secret_value(), algorithm=settings.jwt_algorithm)
    return token, expires_in


def decode_access_token(token: str, settings: Settings) -> dict[str, Any]:
    try:
        return jwt.decode(token, settings.secret_key.get_secret_value(), algorithms=[settings.jwt_algorithm])
    except jwt.ExpiredSignatureError as exc:
        raise AuthenticationError("Token has expired") from exc
    except jwt.PyJWTError as exc:
        raise AuthenticationError("Invalid authentication token") from exc
