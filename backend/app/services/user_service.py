"""User service: registration + authentication (skeleton)."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.schemas.user import UserCreate, UserLogin


def get_user_by_username(db: Session, username: str) -> User | None:
    stmt = select(User).where(User.username == username)
    return db.scalars(stmt).first()


def register(db: Session, payload: UserCreate) -> User:
    if get_user_by_username(db, payload.username) is not None:
        raise ValueError("用户名已存在")
    user = User(
        username=payload.username,
        email=payload.email,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate(db: Session, payload: UserLogin) -> str | None:
    user = get_user_by_username(db, payload.username)
    if user is None or not verify_password(payload.password, user.hashed_password):
        return None
    return create_access_token(subject=user.id, extra={"username": user.username})
