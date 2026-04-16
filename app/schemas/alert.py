from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.core.enums import EventType, Severity, VerificationStatus
from app.schemas.common import ORMModel


class AlertIngest(BaseModel):
    property_id: int
    device_id: int | None = None
    alert_type: EventType
    vendor_event_id: str | None = None
    occurred_at: datetime | None = None
    metadata_json: dict = Field(default_factory=dict)
    media_refs: list[str] = Field(default_factory=list)


class AlertRead(ORMModel):
    id: int
    property_id: int
    device_id: int | None
    incident_id: int | None
    alert_type: EventType
    severity: Severity
    verification_status: VerificationStatus
    occurred_at: datetime
    vendor_event_id: str | None
    metadata_json: dict
    media_refs: list
    created_at: datetime
    updated_at: datetime
