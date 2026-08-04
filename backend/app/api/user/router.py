"""User API: register + login."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.user import Token, UserCreate, UserLogin, UserOut
from app.services import user_service

router = APIRouter()


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: Session = Depends(get_db)) -> UserOut:
    try:
        user = user_service.register(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return UserOut.model_validate(user)


@router.post("/login", response_model=Token)
def login(payload: UserLogin, db: Session = Depends(get_db)) -> Token:
    token = user_service.authenticate(db, payload)
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return Token(access_token=token, token_type="bearer", username=payload.username)
