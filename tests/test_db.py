from pathlib import Path

from sqlalchemy import Integer, String, inspect, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base, create_tables, get_db, get_engine


def test_engine_uses_configured_database_url(tmp_path: Path) -> None:
    assert get_engine().url.database == str(tmp_path / "test.db")


def test_get_db_yields_working_session() -> None:
    db_generator = get_db()
    session = next(db_generator)

    assert session.execute(text("SELECT 1")).scalar_one() == 1

    db_generator.close()


def test_create_tables_creates_model_tables() -> None:
    class Sample(Base):
        __tablename__ = "sample"
        id: Mapped[int] = mapped_column(Integer, primary_key=True)
        name: Mapped[str] = mapped_column(String(50))

    try:
        create_tables()

        assert "sample" in inspect(get_engine()).get_table_names()
    finally:
        Base.metadata.remove(Sample.__table__)
