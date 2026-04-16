from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import IncidentStatus
from app.models.entities import Incident
from app.repos.base import Repository


class IncidentRepository(Repository[Incident]):
    def __init__(self) -> None:
        super().__init__(Incident)

    def get_open_for_property(self, db: Session, property_id: int) -> Incident | None:
        stmt = (
            select(Incident)
            .where(Incident.property_id == property_id)
            .where(Incident.status.in_([IncidentStatus.OPEN, IncidentStatus.UNDER_REVIEW, IncidentStatus.VERIFIED]))
            .order_by(Incident.created_at.desc())
        )
        return db.scalar(stmt)
