from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


def _resolve_database_url() -> str:
    """Return an absolute SQLite URL pointing to the bundled DB file."""

    base_dir = Path(__file__).resolve().parent
    db_path = base_dir / "kiosk.db"
    # sqlite expects forward slashes in URLs even on Windows
    return f"sqlite:///{db_path.as_posix()}"


DATABASE_URL = _resolve_database_url()


engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
