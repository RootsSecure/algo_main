from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.enums import Role
from app.core.security import decode_token
from app.models.entities import User
from app.repos.user_repo import UserRepository

DBSession = Annotated[Session, Depends(get_db)]


def get_current_user(
    db: DBSession,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")

    token = authorization.split(" ", 1)[1]
    try:
        payload = decode_token(token)
    except Exception as exc:  # pragma: no cover - FastAPI surface converts to 401
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

    if payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

    user = UserRepository().get(db, int(payload["sub"]))
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not available")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: Role) -> Callable[[CurrentUser], User]:
    def dependency(user: CurrentUser) -> User:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role {user.role.value} cannot access this resource",
            )
        return user

    return dependency
