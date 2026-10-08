from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import User
from app.schemas.auth import LoginRequest, SignupRequest, TokenResponse, UserResponse
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", status_code=status.HTTP_201_CREATED, response_model=UserResponse)
def signup(request: SignupRequest, db: Annotated[Session, Depends(get_db)]) -> User:
    return auth_service.signup(db, request.email, request.password)


@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest, db: Annotated[Session, Depends(get_db)]) -> TokenResponse:
    tokens = auth_service.login(db, request.email, request.password)
    return TokenResponse(access_token=tokens.access_token, refresh_token=tokens.refresh_token)
