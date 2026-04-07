from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.entities import AuditLog, User


class AuditService:
    def log(
        self,
        db: Session,
        *,
        action: str,
        target_type: str,
        target_id: str,
        actor: User | None = None,
        metadata: dict | None = None,
    ) -> AuditLog:
        entry = AuditLog(
            actor_user_id=actor.id if actor else None,
            action=action,
            target_type=target_type,
            target_id=target_id,
            metadata_json=metadata or {},
        )
        db.add(entry)
        db.flush()
        return entry
