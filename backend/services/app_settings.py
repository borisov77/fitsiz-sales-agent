"""Рантайм-настройки агента: значения можно менять без рестарта.

В `.env` лежит базовое значение, которое используется по умолчанию.
Если через UI выставили override — он хранится в таблице `app_settings`
и перекрывает `.env` до следующего reset'а.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from backend.config import settings
from backend.models.app_setting import AppSetting


# Ключи
KEY_DAILY_LIMIT = "max_cold_emails_per_day"


# ==========================
# Generic
# ==========================
def _get(db: Session, key: str) -> str | None:
    row = db.get(AppSetting, key)
    return row.value if row else None


def _set(db: Session, key: str, value: str) -> None:
    row = db.get(AppSetting, key)
    if row is None:
        row = AppSetting(key=key, value=value, updated_at=datetime.utcnow())
        db.add(row)
    else:
        row.value = value
    db.commit()


def _clear(db: Session, key: str) -> None:
    row = db.get(AppSetting, key)
    if row is not None:
        db.delete(row)
        db.commit()


# ==========================
# Daily limit
# ==========================
def get_daily_limit(db: Session) -> int:
    """Текущий лимит: override из БД или дефолт из .env."""
    raw = _get(db, KEY_DAILY_LIMIT)
    if raw is None:
        return settings.max_cold_emails_per_day
    try:
        return max(0, int(raw))
    except ValueError:
        return settings.max_cold_emails_per_day


def set_daily_limit(db: Session, value: int) -> int:
    """Устанавливает override. Минимум 0, максимум 10 000 (санити).
    Возвращает фактически применённое значение."""
    v = max(0, min(10_000, int(value)))
    _set(db, KEY_DAILY_LIMIT, str(v))
    return v


def reset_daily_limit(db: Session) -> int:
    """Удаляет override — возвращаемся к значению из .env."""
    _clear(db, KEY_DAILY_LIMIT)
    return settings.max_cold_emails_per_day


def has_daily_limit_override(db: Session) -> bool:
    return _get(db, KEY_DAILY_LIMIT) is not None
