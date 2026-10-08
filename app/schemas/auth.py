from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

# 발급하는 토큰보다 충분히 길게 두고, 비정상적으로 긴 입력은 검증 단계에서 막는다
MAX_REFRESH_TOKEN_LENGTH = 2048


class SignupRequest(BaseModel):
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    # 형식 오류도 INVALID_CREDENTIALS로 처리하므로 EmailStr로 검증하지 않는다 (ADR 0008)
    email: str
    password: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(max_length=MAX_REFRESH_TOKEN_LENGTH)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"
