from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.enums import DispatchStatus, IncidentStatus, Severity, VerificationStatus
from app.models.entities import Alert, Evidence, Incident, Partner, PartnerDispatch, Property, User
from app.repos.incident_repo import IncidentRepository
from app.schemas.incident import DispatchCreate, DispatchUpdate, EvidenceCreate, IncidentStatusUpdate, IncidentVerifyRequest
from app.services.audit_service import AuditService
from app.services.notification_service import NotificationService


class IncidentService:
    def __init__(self) -> None:
        self.incidents = IncidentRepository()
        self.audit = AuditService()
        self.notifications = NotificationService()

    def get_or_create_incident(
        self,
        db: Session,
        *,
        property_: Property,
        alert: Alert,
        title: str,
        summary: str,
        severity: Severity,
    ) -> Incident:
        incident = self.incidents.get_open_for_property(db, property_.id)
        if incident is None or severity == Severity.CRITICAL:
            incident = Incident(
                property_id=property_.id,
                title=title,
                summary=summary,
                severity=severity,
                status=IncidentStatus.OPEN,
                verification_status=VerificationStatus.AUTO_VERIFIED if severity == Severity.CRITICAL else VerificationStatus.PENDING,
            )
            db.add(incident)
            db.flush()
        else:
            incident.summary = summary
            if severity == Severity.WARNING and incident.severity == Severity.INFO:
                incident.severity = severity
        alert.incident_id = incident.id
        db.flush()
        if severity == Severity.CRITICAL:
            self.notifications.queue_critical_alerts(db, property_.owner, property_, incident)
        return incident

    def list_incidents(self, db: Session, property_id: int | None = None) -> list[Incident]:
        from sqlalchemy import select

        stmt = select(Incident).order_by(Incident.created_at.desc())
        if property_id:
            stmt = stmt.where(Incident.property_id == property_id)
        return list(db.scalars(stmt))

    def get_incident(self, db: Session, incident_id: int) -> Incident:
        incident = db.get(Incident, incident_id)
        if incident is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")
        return incident

    def verify_incident(self, db: Session, incident: Incident, actor: User, payload: IncidentVerifyRequest) -> Incident:
        incident.verification_status = payload.verification_status
        incident.assigned_ops_user_id = payload.assigned_ops_user_id or actor.id
        incident.status = (
            IncidentStatus.VERIFIED
            if payload.verification_status in {VerificationStatus.AUTO_VERIFIED, VerificationStatus.OPS_VERIFIED}
            else IncidentStatus.DISMISSED
        )
        self.audit.log(
            db,
            action="incident_verified",
            target_type="incident",
            target_id=str(incident.id),
            actor=actor,
            metadata={"verification_status": incident.verification_status.value},
        )
        db.commit()
        db.refresh(incident)
        return incident

    def add_evidence(self, db: Session, incident: Incident, actor: User, payload: EvidenceCreate) -> Evidence:
        evidence = Evidence(incident_id=incident.id, **payload.model_dump())
        db.add(evidence)
        self.audit.log(db, action="evidence_added", target_type="incident", target_id=str(incident.id), actor=actor)
        db.commit()
        db.refresh(evidence)
        return evidence

    def dispatch_partner(self, db: Session, incident: Incident, actor: User, payload: DispatchCreate) -> PartnerDispatch:
        partner = db.get(Partner, payload.partner_id)
        if partner is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Partner not found")
        dispatch = PartnerDispatch(
            incident_id=incident.id,
            partner_id=partner.id,
            eta_minutes=payload.eta_minutes,
            status=DispatchStatus.ACCEPTED,
            accepted_at=datetime.now(UTC),
        )
        incident.status = IncidentStatus.DISPATCHED
        incident.dispatched_at = datetime.now(UTC)
        db.add(dispatch)
        self.audit.log(
            db,
            action="partner_dispatched",
            target_type="incident",
            target_id=str(incident.id),
            actor=actor,
            metadata={"partner_id": partner.id},
        )
        db.commit()
        db.refresh(dispatch)
        return dispatch

    def update_dispatch(self, db: Session, dispatch_id: int, actor: User, payload: DispatchUpdate) -> PartnerDispatch:
        dispatch = db.get(PartnerDispatch, dispatch_id)
        if dispatch is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dispatch not found")
        dispatch.status = payload.status
        dispatch.closure_notes = payload.closure_notes
        dispatch.proof_refs = payload.proof_refs
        now = datetime.now(UTC)
        if payload.status == DispatchStatus.ARRIVED:
            dispatch.arrived_at = now
        if payload.status == DispatchStatus.CLOSED:
            dispatch.closed_at = now
            dispatch.incident.status = IncidentStatus.RESOLVED
            dispatch.incident.resolved_at = now
            dispatch.incident.resolution_code = "partner_closed"
        self.audit.log(
            db,
            action="dispatch_updated",
            target_type="dispatch",
            target_id=str(dispatch.id),
            actor=actor,
            metadata={"status": dispatch.status.value},
        )
        db.commit()
        db.refresh(dispatch)
        return dispatch

    def update_incident_status(self, db: Session, incident: Incident, actor: User, payload: IncidentStatusUpdate) -> Incident:
        incident.status = payload.status
        if payload.status in {IncidentStatus.RESOLVED, IncidentStatus.DISMISSED}:
            incident.resolved_at = datetime.now(UTC)
        if payload.resolution_code:
            incident.resolution_code = payload.resolution_code
        self.audit.log(
            db,
            action="incident_status_updated",
            target_type="incident",
            target_id=str(incident.id),
            actor=actor,
            metadata={"status": incident.status.value},
        )
        db.commit()
        db.refresh(incident)
        return incident

    def export_summary(self, incident: Incident) -> dict:
        return {
            "incident_id": incident.id,
            "property_id": incident.property_id,
            "title": incident.title,
            "summary": incident.summary,
            "severity": incident.severity.value,
            "status": incident.status.value,
            "verification_status": incident.verification_status.value,
            "resolution_code": incident.resolution_code,
            "evidences": [
                {
                    "evidence_id": evidence.id,
                    "file_type": evidence.file_type,
                    "captured_at": evidence.captured_at.isoformat(),
                    "checksum": evidence.checksum,
                    "storage_ref": evidence.storage_ref,
                }
                for evidence in incident.evidences
            ],
            "dispatches": [
                {
                    "dispatch_id": dispatch.id,
                    "partner_id": dispatch.partner_id,
                    "status": dispatch.status.value,
                    "eta_minutes": dispatch.eta_minutes,
                    "proof_refs": dispatch.proof_refs,
                }
                for dispatch in incident.dispatches
            ],
        }
