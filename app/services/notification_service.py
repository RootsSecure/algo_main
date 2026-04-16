from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.enums import NotificationChannel, NotificationStatus
from app.models.entities import Incident, NotificationLog, Property, User


class NotificationService:
    def queue_critical_alerts(
        self,
        db: Session,
        owner: User,
        property_: Property,
        incident: Incident,
    ) -> list[NotificationLog]:
        message = (
            f"Critical incident detected at {property_.name}. "
            f"Severity={incident.severity.value}, incident_id={incident.id}."
        )
        logs: list[NotificationLog] = []
        for channel in (NotificationChannel.PUSH, NotificationChannel.WHATSAPP, NotificationChannel.SMS):
            log = NotificationLog(
                user_id=owner.id,
                property_id=property_.id,
                incident_id=incident.id,
                channel=channel,
                status=NotificationStatus.SENT if channel != NotificationChannel.SMS else NotificationStatus.QUEUED,
                provider="mock-provider",
                message=message,
            )
            db.add(log)
            logs.append(log)
        db.flush()
        return logs
