from typing import Annotated

from fastapi import APIRouter, Depends

from app.models import User
from app.routers.dependencies import get_current_user
from app.schemas.auth import UserResponse

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
def read_me(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    return current_user
