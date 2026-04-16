from __future__ import annotations

from sqlalchemy import inspect
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.enums import Role
from app.core.security import hash_password
from app.models.entities import User
from app.repos.user_repo import UserRepository


class BootstrapService:
    def seed_default_users(self, db: Session) -> None:
        inspector = inspect(db.bind)
        if "users" not in inspector.get_table_names():
            return

        settings = get_settings()
        repo = UserRepository()
        defaults = [
            (settings.default_owner_email, settings.default_owner_password, "Default Owner", Role.OWNER),
            (settings.default_ops_admin_email, settings.default_ops_admin_password, "Default Ops Admin", Role.OPS_ADMIN),
        ]
        created = False
        for email, password, full_name, role in defaults:
            if repo.get_by_email(db, email):
                continue
            db.add(
                User(
                    full_name=full_name,
                    email=email,
                    password_hash=hash_password(password),
                    role=role,
                    is_active=True,
                )
            )
            created = True
        if created:
            db.commit()
