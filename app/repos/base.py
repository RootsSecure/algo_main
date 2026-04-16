from __future__ import annotations

from typing import Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class Repository(Generic[ModelType]):
    def __init__(self, model: type[ModelType]):
        self.model = model

    def get(self, db: Session, entity_id: int) -> ModelType | None:
        return db.get(self.model, entity_id)

    def list(self, db: Session, *, offset: int = 0, limit: int = 100) -> list[ModelType]:
        return list(db.scalars(select(self.model).offset(offset).limit(limit)))

    def add(self, db: Session, instance: ModelType) -> ModelType:
        db.add(instance)
        db.flush()
        db.refresh(instance)
        return instance
