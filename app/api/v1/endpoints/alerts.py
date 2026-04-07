from fastapi import APIRouter, Depends

from app.core.dependencies import CurrentUser, DBSession, require_roles
from app.core.enums import Role, Severity, VerificationStatus
from app.models.entities import User
from app.schemas.alert import AlertIngest, AlertRead
from app.services.alert_service import AlertService
from app.services.property_service import PropertyService

router = APIRouter()
alert_service = AlertService()
property_service = PropertyService()


@router.post("/ingest", response_model=AlertRead)
def ingest_alert(
    payload: AlertIngest,
    db: DBSession,
    current_user: User = Depends(require_roles(Role.OWNER, Role.OPS_ADMIN, Role.INSTALLER)),
) -> AlertRead:
    property_ = property_service.get_property(db, payload.property_id, current_user)
    return AlertRead.model_validate(alert_service.ingest(db, property_, current_user, payload))


@router.get("", response_model=list[AlertRead])
def list_alerts(
    db: DBSession,
    current_user: CurrentUser,
    property_id: int | None = None,
    severity: Severity | None = None,
    verification_status: VerificationStatus | None = None,
) -> list[AlertRead]:
    if property_id:
        property_service.get_property(db, property_id, current_user)
    alerts = alert_service.list_alerts(
        db,
        property_id=property_id,
        severity=severity,
        verification_status=verification_status,
    )
    return [AlertRead.model_validate(alert) for alert in alerts]
