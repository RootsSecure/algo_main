from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import EventType, Severity, VerificationStatus
from app.models.entities import Alert, Device, Property, User
from app.schemas.alert import AlertIngest
from app.services.audit_service import AuditService
from app.services.incident_service import IncidentService


class AlertService:
    def __init__(self) -> None:
        self.audit = AuditService()
        self.incidents = IncidentService()

    def _metadata_severity_override(self, payload: AlertIngest) -> Severity | None:
        override = str(payload.metadata_json.get("recommended_severity", "")).strip().lower()
        if override == Severity.CRITICAL.value:
            return Severity.CRITICAL
        if override == Severity.WARNING.value:
            return Severity.WARNING
        if override == Severity.INFO.value:
            return Severity.INFO
        return None

    def classify_severity(self, payload: AlertIngest, recent_alert_count: int) -> Severity:
        metadata_override = self._metadata_severity_override(payload)
        if metadata_override is not None:
            return metadata_override
        if payload.alert_type in {EventType.TAMPER, EventType.GATE_BREACH}:
            return Severity.CRITICAL
        if payload.alert_type == EventType.OFFLINE:
            return Severity.WARNING
        if payload.alert_type == EventType.MOTION and recent_alert_count >= 2:
            return Severity.CRITICAL
        if payload.alert_type == EventType.MOTION:
            return Severity.WARNING
        return Severity.INFO

    def ingest(self, db: Session, property_: Property, actor: User, payload: AlertIngest) -> Alert:
        recent_alert_count = len(
            list(
                db.scalars(
                    select(Alert).where(Alert.property_id == property_.id).order_by(Alert.created_at.desc()).limit(3)
                )
            )
        )
        severity = self.classify_severity(payload, recent_alert_count)
        occurred_at = payload.occurred_at or datetime.now(UTC)
        device = db.get(Device, payload.device_id) if payload.device_id else None
        alert = Alert(
            property_id=property_.id,
            device_id=device.id if device else None,
            alert_type=payload.alert_type,
            severity=severity,
            verification_status=VerificationStatus.AUTO_VERIFIED if severity == Severity.CRITICAL else VerificationStatus.PENDING,
            occurred_at=occurred_at,
            vendor_event_id=payload.vendor_event_id,
            metadata_json=payload.metadata_json,
            media_refs=payload.media_refs,
        )
        db.add(alert)
        db.flush()
        incident = self.incidents.get_or_create_incident(
            db,
            property_=property_,
            alert=alert,
            title=f"{payload.alert_type.value.replace('_', ' ').title()} detected",
            summary=f"{payload.alert_type.value} detected at {property_.name}",
            severity=severity,
        )
        self.audit.log(
            db,
            action="alert_ingested",
            target_type="alert",
            target_id=str(alert.id),
            actor=actor,
            metadata={"incident_id": incident.id, "severity": severity.value},
        )
        db.commit()
        db.refresh(alert)
        return alert

    def list_alerts(
        self,
        db: Session,
        *,
        property_id: int | None = None,
        severity: Severity | None = None,
        verification_status: VerificationStatus | None = None,
    ) -> list[Alert]:
        stmt = select(Alert).order_by(Alert.occurred_at.desc())
        if property_id:
            stmt = stmt.where(Alert.property_id == property_id)
        if severity:
            stmt = stmt.where(Alert.severity == severity)
        if verification_status:
            stmt = stmt.where(Alert.verification_status == verification_status)
        return list(db.scalars(stmt))
