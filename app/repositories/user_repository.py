from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalars(select(User).where(User.email == email)).one_or_none()


def add_user(db: Session, email: str, password_hash: str, created_at: datetime) -> User:
    user = User(email=email, password_hash=password_hash, created_at=created_at)
    db.add(user)
    return user


def get_user_by_id(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)
