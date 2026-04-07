from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import (
    create_device_provisioning_token,
    create_device_session_token,
    decode_token,
    generate_token_id,
)
from app.models.entities import Device, User
from app.schemas.alert import AlertIngest
from app.schemas.gateway import (
    GatewayEventRequest,
    GatewayHeartbeatRequest,
    GatewayProvisionResponse,
    RaspberryPiConnectRequest,
    RaspberryPiConnectResponse,
)
from app.services.alert_service import AlertService
from app.services.audit_service import AuditService

settings = get_settings()


class GatewayService:
    def __init__(self) -> None:
        self.audit = AuditService()
        self.alerts = AlertService()

    def issue_provisioning_token(self, db: Session, device: Device, actor: User, hardware_id: str | None) -> GatewayProvisionResponse:
        device.gateway_enabled = True
        if hardware_id:
            device.gateway_hardware_id = hardware_id
        jti = generate_token_id()
        device.gateway_token_jti = jti
        token = create_device_provisioning_token(
            str(device.id),
            {
                "jti": jti,
                "hardware_id": device.gateway_hardware_id,
                "aud": "raspberry_pi_gateway",
            },
        )
        self.audit.log(
            db,
            action="gateway_provisioned",
            target_type="device",
            target_id=str(device.id),
            actor=actor,
            metadata={"hardware_id": device.gateway_hardware_id},
        )
        db.commit()
        db.refresh(device)
        return GatewayProvisionResponse(
            device_id=device.id,
            provisioning_token=token,
            expires_in_minutes=settings.device_provisioning_token_expire_minutes,
            gateway_enabled=device.gateway_enabled,
            hardware_id=device.gateway_hardware_id,
            connect_endpoint="/api/v1/gateway/raspberry-pi/connect",
        )

    def _validate_token(self, token: str, token_type: str) -> dict:
        try:
            claims = decode_token(token)
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid gateway token") from exc
        if claims.get("type") != token_type:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid gateway token type")
        if claims.get("aud") != "raspberry_pi_gateway":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid gateway audience")
        return claims

    def connect(self, db: Session, provisioning_token: str, payload: RaspberryPiConnectRequest) -> RaspberryPiConnectResponse:
        claims = self._validate_token(provisioning_token, "device_provisioning")
        device = db.get(Device, int(claims["sub"]))
        if device is None or not device.gateway_enabled:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gateway device not available")
        if device.gateway_token_jti != claims.get("jti"):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Provisioning token has been rotated")
        bound_hardware_id = device.gateway_hardware_id or claims.get("hardware_id")
        if bound_hardware_id and bound_hardware_id != payload.hardware_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Hardware identifier mismatch")
        device.gateway_hardware_id = payload.hardware_id
        device.gateway_last_seen_at = datetime.now(UTC)
        device.gateway_last_ip = payload.ip_address
        device.network_status = payload.network_status
        device.power_status = payload.power_status
        device.battery_level = payload.battery_level
        device.last_heartbeat = datetime.now(UTC)
        device.metadata_json = {
            **device.metadata_json,
            **payload.metadata_json,
            "gateway_client_version": payload.client_version,
            "camera_model": payload.camera_model,
        }
        session_jti = generate_token_id()
        device.gateway_session_jti = session_jti
        session_token = create_device_session_token(
            str(device.id),
            {
                "jti": session_jti,
                "hardware_id": payload.hardware_id,
                "aud": "raspberry_pi_gateway",
            },
        )
        db.commit()
        db.refresh(device)
        return RaspberryPiConnectResponse(
            device_id=device.id,
            property_id=device.property_id,
            session_token=session_token,
            expires_in_minutes=settings.device_session_token_expire_minutes,
            heartbeat_endpoint=f"/api/v1/gateway/raspberry-pi/devices/{device.id}/heartbeat",
            event_endpoint=f"/api/v1/gateway/raspberry-pi/devices/{device.id}/events",
            documentation_endpoint="/project-docs/content/api/raspberry-pi-gateway.md",
        )

    def authenticate_session(self, db: Session, session_token: str, device_id: int) -> Device:
        claims = self._validate_token(session_token, "device_session")
        if int(claims["sub"]) != device_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Gateway token does not match device")
        device = db.get(Device, device_id)
        if device is None or not device.gateway_enabled:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gateway device not available")
        if device.gateway_session_jti != claims.get("jti"):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Gateway session expired or rotated")
        if device.gateway_hardware_id and claims.get("hardware_id") != device.gateway_hardware_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Gateway hardware mismatch")
        return device

    def record_gateway_heartbeat(self, db: Session, device: Device, payload: GatewayHeartbeatRequest) -> Device:
        device.network_status = payload.network_status
        device.power_status = payload.power_status
        device.battery_level = payload.battery_level
        device.gateway_last_ip = payload.ip_address
        device.gateway_last_seen_at = datetime.now(UTC)
        device.last_heartbeat = datetime.now(UTC)
        device.metadata_json = {**device.metadata_json, **payload.metadata_json}
        db.commit()
        db.refresh(device)
        return device

    def ingest_gateway_event(self, db: Session, device: Device, payload: GatewayEventRequest) -> dict:
        alert = self.alerts.ingest(
            db,
            device.property,
            actor=device.property.owner,
            payload=AlertIngest(
                property_id=device.property_id,
                device_id=device.id,
                alert_type=payload.alert_type,
                vendor_event_id=payload.vendor_event_id,
                occurred_at=payload.occurred_at,
                metadata_json={**payload.metadata_json, "source": "raspberry_pi_gateway"},
                media_refs=payload.media_refs,
            ),
        )
        return {
            "alert_id": alert.id,
            "incident_id": alert.incident_id,
            "severity": alert.severity.value,
            "verification_status": alert.verification_status.value,
        }
