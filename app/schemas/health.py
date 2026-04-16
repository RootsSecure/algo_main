from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.core.enums import HealthStatus
from app.schemas.common import ORMModel


class SiteHealthCheckRead(ORMModel):
    id: int
    property_id: int
    check_type: str
    result: HealthStatus
    notes: str
    generated_at: datetime
    remediation_action: str | None
    created_at: datetime
    updated_at: datetime


class PropertyHealthSummary(BaseModel):
    property_id: int
    device_count: int
    offline_devices: int
    latest_status: str
    last_check: datetime | None


class DeviceHealthSummary(BaseModel):
    device_id: int
    serial_number: str
    power_status: str
    network_status: str
    battery_level: int | None
    last_heartbeat: datetime | None
