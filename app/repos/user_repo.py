from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import User
from app.repos.base import Repository


class UserRepository(Repository[User]):
    def __init__(self) -> None:
        super().__init__(User)

    def get_by_email(self, db: Session, email: str) -> User | None:
        return db.scalar(select(User).where(User.email == email))

    def get_by_invite_token(self, db: Session, token: str) -> User | None:
        return db.scalar(select(User).where(User.invite_token == token))
