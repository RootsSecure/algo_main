from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import Device, Property, SiteHealthCheck
from app.schemas.health import DeviceHealthSummary, PropertyHealthSummary


class HealthService:
    def property_summary(self, db: Session, property_: Property) -> PropertyHealthSummary:
        devices = list(db.scalars(select(Device).where(Device.property_id == property_.id)))
        latest = db.scalar(
            select(SiteHealthCheck)
            .where(SiteHealthCheck.property_id == property_.id)
            .order_by(SiteHealthCheck.generated_at.desc())
        )
        offline_devices = sum(1 for device in devices if device.network_status != "online")
        return PropertyHealthSummary(
            property_id=property_.id,
            device_count=len(devices),
            offline_devices=offline_devices,
            latest_status=latest.result.value if latest else "unknown",
            last_check=latest.generated_at if latest else None,
        )

    def device_summaries(self, db: Session, property_id: int | None = None) -> list[DeviceHealthSummary]:
        stmt = select(Device).order_by(Device.created_at.desc())
        if property_id:
            stmt = stmt.where(Device.property_id == property_id)
        devices = list(db.scalars(stmt))
        return [
            DeviceHealthSummary(
                device_id=device.id,
                serial_number=device.serial_number,
                power_status=device.power_status,
                network_status=device.network_status,
                battery_level=device.battery_level,
                last_heartbeat=device.last_heartbeat,
            )
            for device in devices
        ]

    def stale_devices(self, db: Session, minutes: int = 30) -> list[Device]:
        threshold = datetime.now(UTC) - timedelta(minutes=minutes)
        return list(
            db.scalars(
                select(Device)
                .where((Device.last_heartbeat.is_(None)) | (Device.last_heartbeat < threshold))
                .order_by(Device.created_at.desc())
            )
        )
