from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import User
from app.services import auth_service

# auto_error=True면 헤더가 없을 때 스펙에 없는 HTTPException이 나가므로 직접 처리한다
bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    if credentials is None:
        # HTTPBearer는 헤더가 없을 때와 Bearer 형식이 아닐 때 모두 None을 준다
        if request.headers.get("Authorization", "").strip():
            raise auth_service.invalid_token_error()
        raise auth_service.unauthorized_error()
    return auth_service.get_current_user(db, credentials.credentials)
