from fastapi import APIRouter, Depends, Header, HTTPException, status

from app.core.dependencies import DBSession, require_roles
from app.core.enums import Role
from app.models.entities import User
from app.schemas.device import DeviceRead
from app.schemas.gateway import (
    GatewayEventRequest,
    GatewayHeartbeatRequest,
    GatewayProvisionRequest,
    GatewayProvisionResponse,
    RaspberryPiConnectRequest,
    RaspberryPiConnectResponse,
)
from app.services.device_service import DeviceService
from app.services.gateway_service import GatewayService

router = APIRouter()
device_service = DeviceService()
gateway_service = GatewayService()


def _extract_bearer_token(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing gateway bearer token")
    return authorization.split(" ", 1)[1]


@router.post("/devices/{device_id}/provision", response_model=GatewayProvisionResponse)
def provision_gateway(
    device_id: int,
    payload: GatewayProvisionRequest,
    db: DBSession,
    current_user: User = Depends(require_roles(Role.OWNER, Role.OPS_ADMIN)),
) -> GatewayProvisionResponse:
    device = device_service.get_device(db, device_id)
    return gateway_service.issue_provisioning_token(db, device, current_user, payload.hardware_id)


@router.post("/raspberry-pi/connect", response_model=RaspberryPiConnectResponse)
def raspberry_pi_connect(
    payload: RaspberryPiConnectRequest,
    db: DBSession,
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> RaspberryPiConnectResponse:
    provisioning_token = _extract_bearer_token(authorization)
    return gateway_service.connect(db, provisioning_token, payload)


@router.post("/raspberry-pi/devices/{device_id}/heartbeat", response_model=DeviceRead)
def raspberry_pi_heartbeat(
    device_id: int,
    payload: GatewayHeartbeatRequest,
    db: DBSession,
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> DeviceRead:
    session_token = _extract_bearer_token(authorization)
    device = gateway_service.authenticate_session(db, session_token, device_id)
    return DeviceRead.model_validate(gateway_service.record_gateway_heartbeat(db, device, payload))


@router.post("/raspberry-pi/devices/{device_id}/events", response_model=dict)
def raspberry_pi_event(
    device_id: int,
    payload: GatewayEventRequest,
    db: DBSession,
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> dict:
    session_token = _extract_bearer_token(authorization)
    device = gateway_service.authenticate_session(db, session_token, device_id)
    return gateway_service.ingest_gateway_event(db, device, payload)
