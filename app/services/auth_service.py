from __future__ import annotations

import secrets

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.enums import Role
from app.core.security import create_access_token, create_refresh_token, hash_password, verify_password
from app.models.entities import User
from app.repos.user_repo import UserRepository
from app.schemas.auth import AcceptInviteRequest, InviteDelegateRequest, LoginRequest, UserRegistration
from app.services.audit_service import AuditService


class AuthService:
    def __init__(self) -> None:
        self.users = UserRepository()
        self.audit = AuditService()

    def register_owner(self, db: Session, payload: UserRegistration) -> User:
        if self.users.get_by_email(db, payload.email):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
        user = User(
            full_name=payload.full_name,
            email=payload.email,
            password_hash=hash_password(payload.password),
            role=Role.OWNER,
            is_active=True,
        )
        db.add(user)
        db.flush()
        self.audit.log(db, action="register_owner", target_type="user", target_id=str(user.id), actor=user)
        db.commit()
        db.refresh(user)
        return user

    def authenticate(self, db: Session, payload: LoginRequest) -> User:
        user = self.users.get_by_email(db, payload.email)
        if user is None or not verify_password(payload.password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is inactive")
        self.audit.log(db, action="login", target_type="user", target_id=str(user.id), actor=user)
        db.commit()
        return user

    def issue_tokens(self, user: User) -> dict[str, str | int]:
        claims = {"role": user.role.value, "email": user.email}
        return {
            "access_token": create_access_token(str(user.id), claims),
            "refresh_token": create_refresh_token(str(user.id), claims),
            "user_id": user.id,
            "role": user.role.value,
        }

    def invite_delegate(self, db: Session, owner: User, payload: InviteDelegateRequest) -> User:
        existing = self.users.get_by_email(db, payload.email)
        if existing and existing.role != Role.DELEGATE:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already in use")

        invite_token = secrets.token_urlsafe(24)
        delegate = existing or User(
            full_name=payload.full_name,
            email=payload.email,
            password_hash=hash_password(invite_token),
            role=Role.DELEGATE,
            is_active=False,
            invited_by_id=owner.id,
        )
        delegate.full_name = payload.full_name
        delegate.invite_token = invite_token
        delegate.invited_by_id = owner.id
        db.add(delegate)
        db.flush()
        self.audit.log(
            db,
            action="invite_delegate",
            target_type="user",
            target_id=str(delegate.id),
            actor=owner,
            metadata={"invite_token": invite_token},
        )
        db.commit()
        db.refresh(delegate)
        return delegate

    def accept_invite(self, db: Session, payload: AcceptInviteRequest) -> User:
        user = self.users.get_by_invite_token(db, payload.invite_token)
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invite token not found")
        user.password_hash = hash_password(payload.password)
        user.is_active = True
        user.invite_token = None
        self.audit.log(db, action="accept_invite", target_type="user", target_id=str(user.id), actor=user)
        db.commit()
        db.refresh(user)
        return user
