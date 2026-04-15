"""SQLAlchemy engine, сессии и декларативная база."""
from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session

from backend.config import settings, BASE_DIR


# Для SQLite относительный путь из .env разворачиваем от корня проекта,
# чтобы БД лежала в ./data/ вне зависимости от CWD.
def _resolve_database_url(url: str) -> str:
    if url.startswith("sqlite:///./"):
        rel = url.replace("sqlite:///./", "")
        abs_path = (BASE_DIR / rel).resolve()
        abs_path.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{abs_path}"
    return url


DATABASE_URL = _resolve_database_url(settings.database_url)

# check_same_thread нужен только для SQLite (многопоточный uvicorn)
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    """Базовый класс для всех ORM-моделей."""

    pass


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: отдаёт сессию и закрывает после запроса."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Создаёт все таблицы (для старта без Alembic)."""
    # Импорт моделей нужен, чтобы они зарегистрировались в Base.metadata
    from backend.models import lead, message, campaign, document  # noqa: F401

    Base.metadata.create_all(bind=engine)
