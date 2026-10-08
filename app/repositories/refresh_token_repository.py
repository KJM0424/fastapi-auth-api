from datetime import datetime

from sqlalchemy import delete, select
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


def get_refresh_token_by_jti(db: Session, jti: str) -> RefreshToken | None:
    return db.scalars(select(RefreshToken).where(RefreshToken.jti == jti)).one_or_none()


def delete_refresh_token(db: Session, refresh_token_id: int) -> int:
    """삭제한 행 수를 반환한다. 동시 요청으로 이미 삭제됐으면 0이다."""
    result = db.execute(delete(RefreshToken).where(RefreshToken.id == refresh_token_id))
    return result.rowcount
