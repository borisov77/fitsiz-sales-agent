"""Антиспам-помощники: лимиты отправки, рандомные задержки.

Правила из README §6.2:
  - максимум 20 новых cold-писем в день
  - 3-7 минут между письмами (для плановой рассылки)
  - 15-45 минут задержки перед ответом на входящее
  - IMAP-чек каждые 10 минут
"""
from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.config import settings
from backend.models.message import Message, MessageDirection, MessageStatus


# ==========================
# Рандомные задержки
# ==========================
def random_cold_delay_sec() -> int:
    """Секунды задержки между двумя cold-письмами (3-7 мин по умолчанию)."""
    lo = settings.min_delay_between_emails_sec
    hi = max(lo, settings.max_delay_between_emails_sec)
    return random.randint(lo, hi)


def random_reply_delay_sec() -> int:
    """Секунды задержки перед ответом на входящее (15-45 мин)."""
    lo = settings.min_reply_delay_sec
    hi = max(lo, settings.max_reply_delay_sec)
    return random.randint(lo, hi)


# ==========================
# Дневной лимит cold-писем
# ==========================
def _utc_day_start(now: datetime | None = None) -> datetime:
    now = now or datetime.utcnow()
    return datetime(now.year, now.month, now.day)


def count_outgoing_sent_today(db: Session, now: datetime | None = None) -> int:
    """Сколько исходящих писем ушло за сегодня (по UTC)."""
    day_start = _utc_day_start(now)
    stmt = (
        select(func.count(Message.id))
        .where(Message.direction == MessageDirection.outgoing)
        .where(Message.status == MessageStatus.sent)
        .where(Message.sent_at >= day_start)
    )
    return int(db.execute(stmt).scalar_one() or 0)


def under_daily_limit(
    db: Session, limit: int | None = None, now: datetime | None = None
) -> bool:
    """True, если можно отправить ещё одно cold-письмо сегодня."""
    effective_limit = limit if limit is not None else settings.max_cold_emails_per_day
    return count_outgoing_sent_today(db, now=now) < effective_limit


def remaining_daily_quota(
    db: Session, limit: int | None = None, now: datetime | None = None
) -> int:
    """Сколько ещё писем можно отправить сегодня."""
    effective_limit = limit if limit is not None else settings.max_cold_emails_per_day
    sent = count_outgoing_sent_today(db, now=now)
    return max(0, effective_limit - sent)


# ==========================
# Плановое время следующей отправки
# ==========================
def schedule_next_cold_send(
    db: Session, after: datetime | None = None
) -> datetime:
    """Возвращает момент, когда можно отправить следующее cold-письмо.

    Берётся `sent_at` последнего исходящего + рандомная задержка.
    Если ничего ещё не отправлено — возвращает `after` (или сейчас).
    """
    after = after or datetime.utcnow()
    last_sent = db.execute(
        select(Message.sent_at)
        .where(Message.direction == MessageDirection.outgoing)
        .where(Message.status == MessageStatus.sent)
        .where(Message.sent_at.is_not(None))
        .order_by(Message.sent_at.desc())
        .limit(1)
    ).scalar_one_or_none()

    base = last_sent if last_sent and last_sent > after else after
    delay = random_cold_delay_sec()
    return base + timedelta(seconds=delay)


# Совместимость с таймзонами — при желании вызывающая сторона получает aware dt
def to_utc_aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)
