"""Password hashing (bcrypt) and JWT helpers."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt

from backend.core.config import settings


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8")[:72], bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8")[:72], password_hash.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(user_id: int, role: str) -> str:
    cfg = settings()
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=cfg.access_token_expire_minutes),
    }
    return jwt.encode(payload, cfg.secret_key, algorithm=cfg.algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    cfg = settings()
    return jwt.decode(token, cfg.secret_key, algorithms=[cfg.algorithm])
