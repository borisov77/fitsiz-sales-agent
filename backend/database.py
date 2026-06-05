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
    from backend.models import (  # noqa: F401
        app_setting,
        campaign,
        document,
        lead,
        message,
        user,
    )

    Base.metadata.create_all(bind=engine)
    _ensure_columns()


def _ensure_columns() -> None:
    """Лёгкая авто-миграция для SQLite/dev: добавляет недостающие колонки.

    create_all() не меняет уже созданные таблицы, поэтому для добавленных полей
    (например leads.description) нужен идемпотентный ALTER. Это хак уровня
    SQLite-dev: типы тут SQLite-специфичны (DATETIME и т.п.). На Postgres схему
    ведём через нормальные миграции (DDL применяется отдельно), а create_all
    создаёт все колонки сразу — поэтому на не-SQLite просто выходим.
    """
    if not engine.url.get_backend_name().startswith("sqlite"):
        return

    from sqlalchemy import inspect, text

    # (таблица, колонка, SQL-тип) — добавляем, если колонки ещё нет
    expected: list[tuple[str, str, str]] = [
        ("leads", "description", "TEXT"),
        ("leads", "cold_stage", "VARCHAR(20)"),
        ("leads", "close_reason", "TEXT"),
        ("leads", "closed_at", "DATETIME"),
    ]
    inspector = inspect(engine)
    with engine.begin() as conn:
        for table, column, sql_type in expected:
            if table not in inspector.get_table_names():
                continue
            existing = {c["name"] for c in inspector.get_columns(table)}
            if column not in existing:
                conn.execute(
                    text(f'ALTER TABLE {table} ADD COLUMN {column} {sql_type}')
                )
