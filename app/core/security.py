from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

from app.core.config import get_settings

settings = get_settings()


def hash_password(password: str, salt: str | None = None) -> str:
    salt_bytes = os.urandom(16) if salt is None else base64.b64decode(salt.encode("utf-8"))
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt_bytes, 120_000)
    return f"{base64.b64encode(salt_bytes).decode('utf-8')}${base64.b64encode(digest).decode('utf-8')}"


def verify_password(password: str, encoded: str) -> bool:
    salt, stored_hash = encoded.split("$", 1)
    candidate = hash_password(password, salt)
    return hmac.compare_digest(candidate, f"{salt}${stored_hash}")


def _create_token(subject: str, minutes: int, token_type: str, extra: dict[str, Any] | None = None) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + timedelta(minutes=minutes),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def create_access_token(subject: str, extra: dict[str, Any] | None = None) -> str:
    return _create_token(subject, settings.access_token_expire_minutes, "access", extra)


def create_refresh_token(subject: str, extra: dict[str, Any] | None = None) -> str:
    return _create_token(subject, settings.refresh_token_expire_minutes, "refresh", extra)


def create_device_provisioning_token(subject: str, extra: dict[str, Any] | None = None) -> str:
    return _create_token(subject, settings.device_provisioning_token_expire_minutes, "device_provisioning", extra)


def create_device_session_token(subject: str, extra: dict[str, Any] | None = None) -> str:
    return _create_token(subject, settings.device_session_token_expire_minutes, "device_session", extra)


def decode_token(token: str) -> dict[str, Any]:
    return jwt.decode(
        token,
        settings.secret_key,
        algorithms=["HS256"],
        options={"verify_aud": False},
    )


def generate_token_id(length: int = 24) -> str:
    return secrets.token_urlsafe(length)
