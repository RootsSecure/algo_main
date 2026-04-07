from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.entities import Property, User
from app.repos.base import Repository


class PropertyRepository(Repository[Property]):
    def __init__(self) -> None:
        super().__init__(Property)

    def list_accessible(self, db: Session, user: User) -> list[Property]:
        stmt = (
            select(Property)
            .options(joinedload(Property.zones), joinedload(Property.devices))
            .where((Property.owner_id == user.id) | (Property.delegates.any(User.id == user.id)))
            .order_by(Property.created_at.desc())
        )
        return list(db.scalars(stmt).unique())

    def get_accessible(self, db: Session, property_id: int, user: User) -> Property | None:
        stmt = (
            select(Property)
            .options(joinedload(Property.zones), joinedload(Property.devices))
            .where(Property.id == property_id)
            .where((Property.owner_id == user.id) | (Property.delegates.any(User.id == user.id)))
        )
        return db.scalar(stmt)
