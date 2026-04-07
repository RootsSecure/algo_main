from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.core.enums import DeviceType
from app.schemas.common import ORMModel


class DeviceCreate(BaseModel):
    property_id: int
    vendor: str
    device_type: DeviceType
    serial_number: str
    install_location: str
    power_status: str = "unknown"
    network_status: str = "unknown"
    battery_level: int | None = Field(default=None, ge=0, le=100)
    metadata_json: dict = Field(default_factory=dict)


class DeviceHeartbeat(BaseModel):
    power_status: str = "healthy"
    network_status: str = "online"
    battery_level: int | None = Field(default=None, ge=0, le=100)
    metadata_json: dict = Field(default_factory=dict)


class DeviceRead(ORMModel):
    id: int
    property_id: int
    vendor: str
    device_type: DeviceType
    serial_number: str
    install_location: str
    power_status: str
    network_status: str
    battery_level: int | None
    metadata_json: dict
    last_heartbeat: datetime | None
    gateway_enabled: bool
    gateway_hardware_id: str | None
    gateway_last_seen_at: datetime | None
    created_at: datetime
    updated_at: datetime
