from fastapi import APIRouter

from app.core.dependencies import CurrentUser, DBSession
from app.schemas.device import DeviceRead
from app.schemas.health import DeviceHealthSummary, PropertyHealthSummary
from app.services.health_service import HealthService
from app.services.property_service import PropertyService

router = APIRouter()
health_service = HealthService()
property_service = PropertyService()


@router.get("/properties/{property_id}", response_model=PropertyHealthSummary)
def property_health(property_id: int, db: DBSession, current_user: CurrentUser) -> PropertyHealthSummary:
    property_ = property_service.get_property(db, property_id, current_user)
    return health_service.property_summary(db, property_)


@router.get("/devices", response_model=list[DeviceHealthSummary])
def device_health(db: DBSession, current_user: CurrentUser, property_id: int | None = None) -> list[DeviceHealthSummary]:
    if property_id:
        property_service.get_property(db, property_id, current_user)
    return health_service.device_summaries(db, property_id)


@router.get("/devices/offline", response_model=list[DeviceRead])
def offline_devices(db: DBSession, current_user: CurrentUser, minutes: int = 30) -> list[DeviceRead]:
    devices = health_service.stale_devices(db, minutes)
    visible: list[DeviceRead] = []
    for device in devices:
        property_service.get_property(db, device.property_id, current_user)
        visible.append(DeviceRead.model_validate(device))
    return visible
