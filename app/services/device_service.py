from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import HealthStatus
from app.models.entities import Device, Property, SiteHealthCheck, User
from app.schemas.device import DeviceCreate, DeviceHeartbeat
from app.services.audit_service import AuditService


class DeviceService:
    def __init__(self) -> None:
        self.audit = AuditService()

    def register_device(self, db: Session, property_: Property, actor: User, payload: DeviceCreate) -> Device:
        duplicate = db.scalar(select(Device).where(Device.serial_number == payload.serial_number))
        if duplicate:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Device serial already exists")
        device = Device(**payload.model_dump())
        db.add(device)
        db.flush()
        self.audit.log(
            db,
            action="device_registered",
            target_type="device",
            target_id=str(device.id),
            actor=actor,
            metadata={"property_id": property_.id, "serial_number": payload.serial_number},
        )
        db.commit()
        db.refresh(device)
        return device

    def list_devices(self, db: Session, property_id: int | None = None) -> list[Device]:
        stmt = select(Device).order_by(Device.created_at.desc())
        if property_id:
            stmt = stmt.where(Device.property_id == property_id)
        return list(db.scalars(stmt))

    def get_device(self, db: Session, device_id: int) -> Device:
        device = db.get(Device, device_id)
        if device is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
        return device

    def record_heartbeat(self, db: Session, device: Device, payload: DeviceHeartbeat) -> Device:
        device.power_status = payload.power_status
        device.network_status = payload.network_status
        device.battery_level = payload.battery_level
        device.metadata_json = {**device.metadata_json, **payload.metadata_json}
        device.last_heartbeat = datetime.now(UTC)
        check = SiteHealthCheck(
            property_id=device.property_id,
            check_type="heartbeat",
            result=HealthStatus.HEALTHY if payload.network_status == "online" else HealthStatus.WARNING,
            notes=f"Heartbeat received for {device.serial_number}",
            remediation_action="Investigate connectivity" if payload.network_status != "online" else None,
        )
        db.add(check)
        db.commit()
        db.refresh(device)
        return device
