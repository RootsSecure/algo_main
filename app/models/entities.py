from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, Column, DateTime, Enum, ForeignKey, Integer, String, Table, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import (
    DeviceType,
    DispatchStatus,
    EventType,
    HealthStatus,
    IncidentStatus,
    NotificationChannel,
    NotificationStatus,
    Role,
    Severity,
    SiteType,
    VerificationStatus,
)
from app.models.base import Base, TimestampMixin

property_delegates = Table(
    "property_delegates",
    Base.metadata,
    Column("property_id", ForeignKey("properties.id"), primary_key=True),
    Column("user_id", ForeignKey("users.id"), primary_key=True),
)


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(512), nullable=False)
    role: Mapped[Role] = mapped_column(Enum(Role), nullable=False, default=Role.OWNER)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    invite_token: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    invited_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    invited_by: Mapped[User | None] = relationship(remote_side=[id], backref="invited_users")
    owned_properties: Mapped[list[Property]] = relationship(back_populates="owner")
    delegated_properties: Mapped[list[Property]] = relationship(
        secondary=property_delegates,
        back_populates="delegates",
    )


class Property(TimestampMixin, Base):
    __tablename__ = "properties"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str] = mapped_column(Text, nullable=False)
    city: Mapped[str] = mapped_column(String(120), nullable=False)
    state: Mapped[str] = mapped_column(String(120), nullable=False)
    country: Mapped[str] = mapped_column(String(120), default="India", nullable=False)
    postal_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    geo_boundary: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    site_type: Mapped[SiteType] = mapped_column(Enum(SiteType), nullable=False)
    risk_profile: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    escalation_plan: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    active_status: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)

    owner: Mapped[User] = relationship(back_populates="owned_properties")
    delegates: Mapped[list[User]] = relationship(
        secondary=property_delegates,
        back_populates="delegated_properties",
    )
    zones: Mapped[list[Zone]] = relationship(back_populates="property", cascade="all, delete-orphan")
    devices: Mapped[list[Device]] = relationship(back_populates="property", cascade="all, delete-orphan")
    alerts: Mapped[list[Alert]] = relationship(back_populates="property", cascade="all, delete-orphan")
    incidents: Mapped[list[Incident]] = relationship(back_populates="property", cascade="all, delete-orphan")
    health_checks: Mapped[list[SiteHealthCheck]] = relationship(
        back_populates="property",
        cascade="all, delete-orphan",
    )


class Zone(TimestampMixin, Base):
    __tablename__ = "zones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    zone_type: Mapped[str] = mapped_column(String(120), nullable=False)
    polygon: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    allowed_activity_window: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    sensitivity_level: Mapped[str] = mapped_column(String(50), default="medium", nullable=False)

    property: Mapped[Property] = relationship(back_populates="zones")


class Device(TimestampMixin, Base):
    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"), nullable=False, index=True)
    vendor: Mapped[str] = mapped_column(String(120), nullable=False)
    device_type: Mapped[DeviceType] = mapped_column(Enum(DeviceType), nullable=False)
    serial_number: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    install_location: Mapped[str] = mapped_column(String(255), nullable=False)
    power_status: Mapped[str] = mapped_column(String(50), default="unknown", nullable=False)
    network_status: Mapped[str] = mapped_column(String(50), default="unknown", nullable=False)
    battery_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    last_heartbeat: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    gateway_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    gateway_hardware_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    gateway_token_jti: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    gateway_session_jti: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    gateway_last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    gateway_last_ip: Mapped[str | None] = mapped_column(String(120), nullable=True)

    property: Mapped[Property] = relationship(back_populates="devices")
    alerts: Mapped[list[Alert]] = relationship(back_populates="device")


class Incident(TimestampMixin, Base):
    __tablename__ = "incidents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[Severity] = mapped_column(Enum(Severity), nullable=False)
    status: Mapped[IncidentStatus] = mapped_column(
        Enum(IncidentStatus),
        nullable=False,
        default=IncidentStatus.OPEN,
    )
    verification_status: Mapped[VerificationStatus] = mapped_column(
        Enum(VerificationStatus),
        nullable=False,
        default=VerificationStatus.PENDING,
    )
    assigned_ops_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    dispatched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolution_code: Mapped[str | None] = mapped_column(String(120), nullable=True)

    property: Mapped[Property] = relationship(back_populates="incidents")
    alerts: Mapped[list[Alert]] = relationship(back_populates="incident")
    evidences: Mapped[list[Evidence]] = relationship(back_populates="incident", cascade="all, delete-orphan")
    dispatches: Mapped[list[PartnerDispatch]] = relationship(
        back_populates="incident",
        cascade="all, delete-orphan",
    )


class Alert(TimestampMixin, Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"), nullable=False, index=True)
    device_id: Mapped[int | None] = mapped_column(ForeignKey("devices.id"), nullable=True, index=True)
    incident_id: Mapped[int | None] = mapped_column(ForeignKey("incidents.id"), nullable=True, index=True)
    alert_type: Mapped[EventType] = mapped_column(Enum(EventType), nullable=False)
    severity: Mapped[Severity] = mapped_column(Enum(Severity), nullable=False)
    verification_status: Mapped[VerificationStatus] = mapped_column(
        Enum(VerificationStatus),
        nullable=False,
        default=VerificationStatus.PENDING,
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    vendor_event_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    media_refs: Mapped[list] = mapped_column(JSON, default=list, nullable=False)

    property: Mapped[Property] = relationship(back_populates="alerts")
    device: Mapped[Device | None] = relationship(back_populates="alerts")
    incident: Mapped[Incident | None] = relationship(back_populates="alerts")


class Evidence(TimestampMixin, Base):
    __tablename__ = "evidences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    incident_id: Mapped[int] = mapped_column(ForeignKey("incidents.id"), nullable=False, index=True)
    file_type: Mapped[str] = mapped_column(String(50), nullable=False)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    checksum: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_ref: Mapped[str] = mapped_column(String(500), nullable=False)
    retention_policy: Mapped[str] = mapped_column(String(120), nullable=False)
    exported: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    incident: Mapped[Incident] = relationship(back_populates="evidences")


class Partner(TimestampMixin, Base):
    __tablename__ = "partners"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    service_area: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str] = mapped_column(String(50), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    dispatches: Mapped[list[PartnerDispatch]] = relationship(back_populates="partner")


class PartnerDispatch(TimestampMixin, Base):
    __tablename__ = "partner_dispatches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    incident_id: Mapped[int] = mapped_column(ForeignKey("incidents.id"), nullable=False, index=True)
    partner_id: Mapped[int] = mapped_column(ForeignKey("partners.id"), nullable=False, index=True)
    status: Mapped[DispatchStatus] = mapped_column(
        Enum(DispatchStatus),
        nullable=False,
        default=DispatchStatus.PENDING,
    )
    eta_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    arrived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closure_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    proof_refs: Mapped[list] = mapped_column(JSON, default=list, nullable=False)

    incident: Mapped[Incident] = relationship(back_populates="dispatches")
    partner: Mapped[Partner] = relationship(back_populates="dispatches")


class SiteHealthCheck(TimestampMixin, Base):
    __tablename__ = "site_health_checks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"), nullable=False, index=True)
    check_type: Mapped[str] = mapped_column(String(120), nullable=False)
    result: Mapped[HealthStatus] = mapped_column(Enum(HealthStatus), nullable=False)
    notes: Mapped[str] = mapped_column(Text, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    remediation_action: Mapped[str | None] = mapped_column(Text, nullable=True)

    property: Mapped[Property] = relationship(back_populates="health_checks")


class NotificationLog(TimestampMixin, Base):
    __tablename__ = "notification_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    property_id: Mapped[int | None] = mapped_column(ForeignKey("properties.id"), nullable=True)
    incident_id: Mapped[int | None] = mapped_column(ForeignKey("incidents.id"), nullable=True)
    channel: Mapped[NotificationChannel] = mapped_column(Enum(NotificationChannel), nullable=False)
    status: Mapped[NotificationStatus] = mapped_column(Enum(NotificationStatus), nullable=False)
    provider: Mapped[str] = mapped_column(String(120), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)


class AuditLog(TimestampMixin, Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(255), nullable=False)
    target_type: Mapped[str] = mapped_column(String(120), nullable=False)
    target_id: Mapped[str] = mapped_column(String(120), nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
