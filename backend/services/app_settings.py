"""Рантайм-настройки агента: значения можно менять без рестарта.

В `.env` лежит базовое значение, которое используется по умолчанию.
Если через UI выставили override — он хранится в таблице `app_settings`
и перекрывает `.env` до следующего reset'а.
"""
from __future__ import annotations

import json
import re
from datetime import datetime

from sqlalchemy.orm import Session

from backend.config import settings
from backend.models.app_setting import AppSetting


# Ключи
KEY_DAILY_LIMIT = "max_cold_emails_per_day"
KEY_MANAGER_EMAILS = "manager_emails"
KEY_AUTO_TRANSFER = "auto_transfer_to_manager"
KEY_AUTO_SEND = "auto_send"
KEY_NEXT_COLD_SEND_AT = "next_cold_send_at"

MAX_MANAGER_EMAILS = 5
_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


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


# ==========================
# Почты менеджеров (до 5, хранятся в БД)
# ==========================
class ManagerEmailsError(ValueError):
    """Невалидный список почт менеджеров."""


def _env_manager_emails() -> list[str]:
    """Фолбэк из .env: MANAGER_EMAIL + MANAGER_EMAIL_CC."""
    out: list[str] = []
    if settings.manager_email:
        out.append(settings.manager_email.strip())
    for cc in settings.manager_cc_list:
        if cc not in out:
            out.append(cc)
    return out[:MAX_MANAGER_EMAILS]


def get_manager_emails(db: Session) -> list[str]:
    """Текущий список почт менеджеров: override из БД или фолбэк из .env."""
    raw = _get(db, KEY_MANAGER_EMAILS)
    if raw is None:
        return _env_manager_emails()
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return [str(e).strip() for e in data if str(e).strip()][:MAX_MANAGER_EMAILS]
    except json.JSONDecodeError:
        pass
    return _env_manager_emails()


def set_manager_emails(db: Session, emails: list[str]) -> list[str]:
    """Валидирует и сохраняет список почт. Дубли убираем, максимум 5."""
    cleaned: list[str] = []
    for e in emails:
        addr = (e or "").strip()
        if not addr:
            continue
        if not _EMAIL_RE.match(addr):
            raise ManagerEmailsError(f"Некорректный email: {addr}")
        if addr.lower() not in {x.lower() for x in cleaned}:
            cleaned.append(addr)
    if len(cleaned) > MAX_MANAGER_EMAILS:
        raise ManagerEmailsError(f"Не более {MAX_MANAGER_EMAILS} адресов")
    _set(db, KEY_MANAGER_EMAILS, json.dumps(cleaned, ensure_ascii=False))
    return cleaned


# ==========================
# Авто-передача менеджеру (тумблер)
# ==========================
def get_auto_transfer(db: Session) -> bool:
    """Включена ли авто-передача warm-лида: override из БД или дефолт из .env."""
    raw = _get(db, KEY_AUTO_TRANSFER)
    if raw is None:
        return settings.auto_transfer_to_manager
    return raw == "1"


def set_auto_transfer(db: Session, enabled: bool) -> bool:
    _set(db, KEY_AUTO_TRANSFER, "1" if enabled else "0")
    return enabled


# ==========================
# Режим отправки AUTO_SEND (тумблер)
# ==========================
def get_auto_send(db: Session) -> bool:
    """Авто-режим отправки: override из БД или дефолт из .env (AUTO_SEND)."""
    raw = _get(db, KEY_AUTO_SEND)
    if raw is None:
        return settings.auto_send
    return raw == "1"


def set_auto_send(db: Session, enabled: bool) -> bool:
    _set(db, KEY_AUTO_SEND, "1" if enabled else "0")
    return enabled


# ==========================
# Тайминг очереди cold-рассылки (антиспам 3-7 мин)
# ==========================
def get_next_cold_send_at(db: Session) -> datetime | None:
    raw = _get(db, KEY_NEXT_COLD_SEND_AT)
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


def set_next_cold_send_at(db: Session, when: datetime) -> None:
    _set(db, KEY_NEXT_COLD_SEND_AT, when.isoformat())
