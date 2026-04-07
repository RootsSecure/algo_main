from fastapi import APIRouter, Depends

from app.core.dependencies import CurrentUser, DBSession, require_roles
from app.core.enums import Role
from app.models.entities import User
from app.schemas.device import DeviceCreate, DeviceHeartbeat, DeviceRead
from app.services.device_service import DeviceService
from app.services.property_service import PropertyService

router = APIRouter()
device_service = DeviceService()
property_service = PropertyService()


@router.post("", response_model=DeviceRead)
def register_device(
    payload: DeviceCreate,
    db: DBSession,
    current_user: User = Depends(require_roles(Role.OWNER, Role.OPS_ADMIN, Role.INSTALLER)),
) -> DeviceRead:
    property_ = property_service.get_property(db, payload.property_id, current_user)
    return DeviceRead.model_validate(device_service.register_device(db, property_, current_user, payload))


@router.get("", response_model=list[DeviceRead])
def list_devices(db: DBSession, current_user: CurrentUser, property_id: int | None = None) -> list[DeviceRead]:
    if property_id:
        property_service.get_property(db, property_id, current_user)
    return [DeviceRead.model_validate(device) for device in device_service.list_devices(db, property_id)]


@router.post("/{device_id}/heartbeat", response_model=DeviceRead)
def heartbeat(device_id: int, payload: DeviceHeartbeat, db: DBSession, current_user: CurrentUser) -> DeviceRead:
    device = device_service.get_device(db, device_id)
    property_service.get_property(db, device.property_id, current_user)
    return DeviceRead.model_validate(device_service.record_heartbeat(db, device, payload))
