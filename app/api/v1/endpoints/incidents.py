from fastapi import APIRouter, Depends

from app.core.dependencies import CurrentUser, DBSession, require_roles
from app.core.enums import Role
from app.models.entities import User
from app.schemas.incident import (
    DispatchCreate,
    DispatchUpdate,
    EvidenceCreate,
    EvidenceRead,
    IncidentRead,
    IncidentStatusUpdate,
    IncidentVerifyRequest,
    PartnerDispatchRead,
)
from app.services.incident_service import IncidentService
from app.services.property_service import PropertyService

router = APIRouter()
incident_service = IncidentService()
property_service = PropertyService()


@router.get("", response_model=list[IncidentRead])
def list_incidents(db: DBSession, current_user: CurrentUser, property_id: int | None = None) -> list[IncidentRead]:
    if property_id:
        property_service.get_property(db, property_id, current_user)
    return [IncidentRead.model_validate(incident) for incident in incident_service.list_incidents(db, property_id)]


@router.post("/{incident_id}/verify", response_model=IncidentRead)
def verify_incident(
    incident_id: int,
    payload: IncidentVerifyRequest,
    db: DBSession,
    current_user: User = Depends(require_roles(Role.OPS_ADMIN, Role.OWNER)),
) -> IncidentRead:
    incident = incident_service.get_incident(db, incident_id)
    property_service.get_property(db, incident.property_id, current_user)
    return IncidentRead.model_validate(incident_service.verify_incident(db, incident, current_user, payload))


@router.post("/{incident_id}/evidence", response_model=EvidenceRead)
def add_evidence(incident_id: int, payload: EvidenceCreate, db: DBSession, current_user: CurrentUser) -> EvidenceRead:
    incident = incident_service.get_incident(db, incident_id)
    property_service.get_property(db, incident.property_id, current_user)
    return EvidenceRead.model_validate(incident_service.add_evidence(db, incident, current_user, payload))


@router.post("/{incident_id}/dispatch", response_model=PartnerDispatchRead)
def dispatch_partner(
    incident_id: int,
    payload: DispatchCreate,
    db: DBSession,
    current_user: User = Depends(require_roles(Role.OPS_ADMIN, Role.OWNER)),
) -> PartnerDispatchRead:
    incident = incident_service.get_incident(db, incident_id)
    property_service.get_property(db, incident.property_id, current_user)
    return PartnerDispatchRead.model_validate(incident_service.dispatch_partner(db, incident, current_user, payload))


@router.patch("/dispatches/{dispatch_id}", response_model=PartnerDispatchRead)
def update_dispatch(dispatch_id: int, payload: DispatchUpdate, db: DBSession, current_user: CurrentUser) -> PartnerDispatchRead:
    return PartnerDispatchRead.model_validate(incident_service.update_dispatch(db, dispatch_id, current_user, payload))


@router.patch("/{incident_id}/status", response_model=IncidentRead)
def update_status(incident_id: int, payload: IncidentStatusUpdate, db: DBSession, current_user: CurrentUser) -> IncidentRead:
    incident = incident_service.get_incident(db, incident_id)
    property_service.get_property(db, incident.property_id, current_user)
    return IncidentRead.model_validate(incident_service.update_incident_status(db, incident, current_user, payload))


@router.get("/{incident_id}/export-summary", response_model=dict)
def export_summary(incident_id: int, db: DBSession, current_user: CurrentUser) -> dict:
    incident = incident_service.get_incident(db, incident_id)
    property_service.get_property(db, incident.property_id, current_user)
    return incident_service.export_summary(incident)
