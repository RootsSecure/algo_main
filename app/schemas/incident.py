from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.core.enums import DispatchStatus, IncidentStatus, Severity, VerificationStatus
from app.schemas.common import ORMModel


class IncidentRead(ORMModel):
    id: int
    property_id: int
    title: str
    summary: str
    severity: Severity
    status: IncidentStatus
    verification_status: VerificationStatus
    assigned_ops_user_id: int | None
    dispatched_at: datetime | None
    resolved_at: datetime | None
    resolution_code: str | None
    created_at: datetime
    updated_at: datetime


class IncidentVerifyRequest(BaseModel):
    verification_status: VerificationStatus
    assigned_ops_user_id: int | None = None


class IncidentStatusUpdate(BaseModel):
    status: IncidentStatus
    resolution_code: str | None = None


class EvidenceCreate(BaseModel):
    file_type: str
    captured_at: datetime
    checksum: str
    storage_ref: str
    retention_policy: str


class DispatchCreate(BaseModel):
    partner_id: int
    eta_minutes: int | None = Field(default=None, ge=0)


class DispatchUpdate(BaseModel):
    status: DispatchStatus
    closure_notes: str | None = None
    proof_refs: list[str] = Field(default_factory=list)


class PartnerRead(ORMModel):
    id: int
    name: str
    service_area: str
    phone: str
    email: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class PartnerCreate(BaseModel):
    name: str
    service_area: str
    phone: str
    email: str


class PartnerDispatchRead(ORMModel):
    id: int
    incident_id: int
    partner_id: int
    status: DispatchStatus
    eta_minutes: int | None
    accepted_at: datetime | None
    arrived_at: datetime | None
    closed_at: datetime | None
    closure_notes: str | None
    proof_refs: list
    created_at: datetime
    updated_at: datetime


class EvidenceRead(ORMModel):
    id: int
    incident_id: int
    file_type: str
    captured_at: datetime
    checksum: str
    storage_ref: str
    retention_policy: str
    exported: bool
    created_at: datetime
    updated_at: datetime
