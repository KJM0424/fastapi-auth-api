from datetime import datetime

from sqlalchemy.orm import Session

from app.models import RefreshToken


def add_refresh_token(
    db: Session,
    user_id: int,
    jti: str,
    token_hash: str,
    expires_at: datetime,
    created_at: datetime,
) -> RefreshToken:
    refresh_token = RefreshToken(
        user_id=user_id,
        jti=jti,
        token_hash=token_hash,
        expires_at=expires_at,
        created_at=created_at,
    )
    db.add(refresh_token)
    return refresh_token
