from datetime import UTC, datetime, timedelta, timezone

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError, StatementError

from app.db.session import create_tables, get_session_factory
from app.models import RefreshToken, User

NOW = datetime(2026, 10, 8, 9, 30, tzinfo=UTC)


@pytest.fixture(autouse=True)
def tables() -> None:
    create_tables()


def _user(email: str = "user@example.com") -> User:
    return User(email=email, password_hash="hash", created_at=NOW)


def test_datetime_is_returned_in_utc() -> None:
    kst = timezone(timedelta(hours=9))
    with get_session_factory()() as session:
        session.add(
            User(email="user@example.com", password_hash="hash", created_at=NOW.astimezone(kst))
        )
        session.commit()

    with get_session_factory()() as session:
        user = session.scalars(select(User)).one()

    assert user.created_at == NOW
    assert user.created_at.tzinfo == UTC


def test_naive_datetime_is_rejected() -> None:
    with get_session_factory()() as session:
        session.add(
            User(email="user@example.com", password_hash="hash", created_at=datetime(2026, 10, 8))
        )

        with pytest.raises(StatementError):
            session.commit()


def test_email_is_unique() -> None:
    with get_session_factory()() as session:
        session.add_all([_user(), _user()])

        with pytest.raises(IntegrityError):
            session.commit()


def test_sqlite_foreign_keys_are_enabled() -> None:
    with get_session_factory()() as session:
        assert session.execute(text("PRAGMA foreign_keys")).scalar_one() == 1
        session.add(
            RefreshToken(
                user_id=999, jti="a" * 32, token_hash="b" * 64, expires_at=NOW, created_at=NOW
            )
        )

        with pytest.raises(IntegrityError):
            session.commit()
