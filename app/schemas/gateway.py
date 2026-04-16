from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.core.enums import EventType


class GatewayProvisionRequest(BaseModel):
    hardware_id: str | None = Field(default=None, max_length=255)


class GatewayProvisionResponse(BaseModel):
    device_id: int
    provisioning_token: str
    token_type: str = "bearer"
    expires_in_minutes: int
    gateway_enabled: bool
    hardware_id: str | None
    connect_endpoint: str


class RaspberryPiConnectRequest(BaseModel):
    hardware_id: str = Field(..., min_length=3, max_length=255)
    network_status: str = "online"
    power_status: str = "healthy"
    battery_level: int | None = Field(default=None, ge=0, le=100)
    ip_address: str | None = Field(default=None, max_length=120)
    client_version: str | None = Field(default=None, max_length=120)
    camera_model: str | None = Field(default=None, max_length=120)
    metadata_json: dict = Field(default_factory=dict)


class RaspberryPiConnectResponse(BaseModel):
    device_id: int
    property_id: int
    session_token: str
    token_type: str = "bearer"
    expires_in_minutes: int
    heartbeat_endpoint: str
    event_endpoint: str
    documentation_endpoint: str


class GatewayHeartbeatRequest(BaseModel):
    network_status: str = "online"
    power_status: str = "healthy"
    battery_level: int | None = Field(default=None, ge=0, le=100)
    ip_address: str | None = Field(default=None, max_length=120)
    metadata_json: dict = Field(default_factory=dict)


class GatewayEventRequest(BaseModel):
    alert_type: EventType
    vendor_event_id: str | None = None
    occurred_at: datetime | None = None
    metadata_json: dict = Field(default_factory=dict)
    media_refs: list[str] = Field(default_factory=list)


class GatewayAuthContext(BaseModel):
    device_id: int
    hardware_id: str | None
