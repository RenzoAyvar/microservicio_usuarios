from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import jwt
from argon2 import PasswordHasher
from fastapi import HTTPException, status
from jwt import InvalidTokenError

from app.config import settings

HASHTER = PasswordHasher()
FAILED_LOGINS: dict[str, dict[str, Any]] = {}


def hash_password(password: str) -> str:
    return HASHTER.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return HASHTER.verify(password_hash, password)
    except Exception:
        return False


def create_access_token(subject: str) -> str:
    expire = datetime.utcnow() + timedelta(hours=settings.access_token_expire_hours)
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> str:
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except InvalidTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido o expirado") from exc

    subject = payload.get("sub")
    if not subject:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido o expirado")
    return str(subject)


def is_account_locked(email: str) -> bool:
    info = FAILED_LOGINS.get(email.lower())
    if not info:
        return False

    locked_until = info.get("locked_until")
    if locked_until and datetime.utcnow() < locked_until:
        return True

    if locked_until and datetime.utcnow() >= locked_until:
        FAILED_LOGINS.pop(email.lower(), None)
    return False


def register_failed_attempt(email: str) -> bool:
    key = email.lower()
    now = datetime.utcnow()
    info = FAILED_LOGINS.get(key, {"count": 0, "locked_until": None})

    if info.get("locked_until") and now < info["locked_until"]:
        return True

    if info.get("locked_until") and now >= info["locked_until"]:
        info = {"count": 0, "locked_until": None}

    info["count"] = info.get("count", 0) + 1
    if info["count"] >= 3:
        info["locked_until"] = now + timedelta(minutes=15)
        info["count"] = 3
    FAILED_LOGINS[key] = info
    return bool(info.get("locked_until") and now < info["locked_until"])


def clear_failed_attempts(email: str) -> None:
    FAILED_LOGINS.pop(email.lower(), None)
