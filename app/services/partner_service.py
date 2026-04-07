from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import Partner, User
from app.schemas.incident import PartnerCreate
from app.services.audit_service import AuditService


class PartnerService:
    def __init__(self) -> None:
        self.audit = AuditService()

    def create_partner(self, db: Session, actor: User, payload: PartnerCreate) -> Partner:
        partner = Partner(**payload.model_dump())
        db.add(partner)
        db.flush()
        self.audit.log(db, action="partner_created", target_type="partner", target_id=str(partner.id), actor=actor)
        db.commit()
        db.refresh(partner)
        return partner

    def list_partners(self, db: Session) -> list[Partner]:
        return list(db.scalars(select(Partner).order_by(Partner.created_at.desc())))
