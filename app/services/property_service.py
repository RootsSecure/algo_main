from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.entities import Property, User, Zone
from app.repos.property_repo import PropertyRepository
from app.repos.user_repo import UserRepository
from app.schemas.property import PropertyCreate, PropertyUpdate, ZoneCreate
from app.services.audit_service import AuditService


class PropertyService:
    def __init__(self) -> None:
        self.properties = PropertyRepository()
        self.users = UserRepository()
        self.audit = AuditService()

    def create_property(self, db: Session, owner: User, payload: PropertyCreate) -> Property:
        property_ = Property(owner_id=owner.id, **payload.model_dump())
        db.add(property_)
        db.flush()
        self.audit.log(db, action="property_created", target_type="property", target_id=str(property_.id), actor=owner)
        db.commit()
        db.refresh(property_)
        return property_

    def list_properties(self, db: Session, user: User) -> list[Property]:
        return self.properties.list_accessible(db, user)

    def get_property(self, db: Session, property_id: int, user: User) -> Property:
        property_ = self.properties.get_accessible(db, property_id, user)
        if property_ is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")
        return property_

    def update_property(self, db: Session, property_: Property, actor: User, payload: PropertyUpdate) -> Property:
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(property_, field, value)
        self.audit.log(db, action="property_updated", target_type="property", target_id=str(property_.id), actor=actor)
        db.commit()
        db.refresh(property_)
        return property_

    def add_zone(self, db: Session, property_: Property, actor: User, payload: ZoneCreate) -> Zone:
        zone = Zone(property_id=property_.id, **payload.model_dump())
        db.add(zone)
        self.audit.log(db, action="zone_added", target_type="property", target_id=str(property_.id), actor=actor)
        db.commit()
        db.refresh(zone)
        return zone

    def assign_delegate(self, db: Session, property_: Property, actor: User, delegate_user_id: int) -> Property:
        delegate = self.users.get(db, delegate_user_id)
        if delegate is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Delegate not found")
        if delegate in property_.delegates:
            return property_
        property_.delegates.append(delegate)
        self.audit.log(
            db,
            action="delegate_assigned",
            target_type="property",
            target_id=str(property_.id),
            actor=actor,
            metadata={"delegate_user_id": delegate.id},
        )
        db.commit()
        db.refresh(property_)
        return property_
