from fastapi import APIRouter, Depends

from app.core.dependencies import CurrentUser, DBSession, require_roles
from app.core.enums import Role
from app.models.entities import User
from app.schemas.incident import PartnerCreate, PartnerRead
from app.services.partner_service import PartnerService

router = APIRouter()
partner_service = PartnerService()


@router.post("", response_model=PartnerRead)
def create_partner(
    payload: PartnerCreate,
    db: DBSession,
    current_user: User = Depends(require_roles(Role.OPS_ADMIN, Role.OWNER)),
) -> PartnerRead:
    return PartnerRead.model_validate(partner_service.create_partner(db, current_user, payload))


@router.get("", response_model=list[PartnerRead])
def list_partners(db: DBSession, current_user: CurrentUser) -> list[PartnerRead]:
    return [PartnerRead.model_validate(partner) for partner in partner_service.list_partners(db)]
