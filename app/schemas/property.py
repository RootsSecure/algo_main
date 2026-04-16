from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.core.enums import SiteType
from app.schemas.common import ORMModel


class ZoneCreate(BaseModel):
    name: str
    zone_type: str
    polygon: dict = Field(default_factory=dict)
    allowed_activity_window: dict = Field(default_factory=dict)
    sensitivity_level: str = "medium"


class ZoneRead(ORMModel):
    id: int
    name: str
    zone_type: str
    polygon: dict
    allowed_activity_window: dict
    sensitivity_level: str
    created_at: datetime
    updated_at: datetime


class PropertyCreate(BaseModel):
    name: str
    address: str
    city: str
    state: str
    country: str = "India"
    postal_code: str | None = None
    geo_boundary: dict = Field(default_factory=dict)
    site_type: SiteType
    risk_profile: dict = Field(default_factory=dict)
    escalation_plan: dict = Field(default_factory=dict)


class PropertyUpdate(BaseModel):
    name: str | None = None
    address: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    postal_code: str | None = None
    geo_boundary: dict | None = None
    risk_profile: dict | None = None
    escalation_plan: dict | None = None
    active_status: bool | None = None


class PropertyRead(ORMModel):
    id: int
    name: str
    address: str
    city: str
    state: str
    country: str
    postal_code: str | None
    geo_boundary: dict
    site_type: SiteType
    risk_profile: dict
    escalation_plan: dict
    active_status: bool
    owner_id: int
    created_at: datetime
    updated_at: datetime
    zones: list[ZoneRead] = Field(default_factory=list)
