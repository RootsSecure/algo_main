from fastapi import APIRouter, Depends

from app.core.dependencies import CurrentUser, DBSession, require_roles
from app.core.enums import Role
from app.models.entities import User
from app.schemas.property import PropertyCreate, PropertyRead, PropertyUpdate, ZoneCreate, ZoneRead
from app.services.property_service import PropertyService

router = APIRouter()
service = PropertyService()


@router.post("", response_model=PropertyRead)
def create_property(
    payload: PropertyCreate,
    db: DBSession,
    current_user: User = Depends(require_roles(Role.OWNER, Role.OPS_ADMIN)),
) -> PropertyRead:
    return PropertyRead.model_validate(service.create_property(db, current_user, payload))


@router.get("", response_model=list[PropertyRead])
def list_properties(db: DBSession, current_user: CurrentUser) -> list[PropertyRead]:
    return [PropertyRead.model_validate(item) for item in service.list_properties(db, current_user)]


@router.get("/{property_id}", response_model=PropertyRead)
def get_property(property_id: int, db: DBSession, current_user: CurrentUser) -> PropertyRead:
    return PropertyRead.model_validate(service.get_property(db, property_id, current_user))


@router.patch("/{property_id}", response_model=PropertyRead)
def update_property(
    property_id: int,
    payload: PropertyUpdate,
    db: DBSession,
    current_user: User = Depends(require_roles(Role.OWNER, Role.OPS_ADMIN)),
) -> PropertyRead:
    property_ = service.get_property(db, property_id, current_user)
    return PropertyRead.model_validate(service.update_property(db, property_, current_user, payload))


@router.post("/{property_id}/zones", response_model=ZoneRead)
def add_zone(
    property_id: int,
    payload: ZoneCreate,
    db: DBSession,
    current_user: User = Depends(require_roles(Role.OWNER, Role.OPS_ADMIN)),
) -> ZoneRead:
    property_ = service.get_property(db, property_id, current_user)
    return ZoneRead.model_validate(service.add_zone(db, property_, current_user, payload))


@router.post("/{property_id}/delegates/{delegate_user_id}", response_model=PropertyRead)
def assign_delegate(
    property_id: int,
    delegate_user_id: int,
    db: DBSession,
    current_user: User = Depends(require_roles(Role.OWNER, Role.OPS_ADMIN)),
) -> PropertyRead:
    property_ = service.get_property(db, property_id, current_user)
    return PropertyRead.model_validate(service.assign_delegate(db, property_, current_user, delegate_user_id))
