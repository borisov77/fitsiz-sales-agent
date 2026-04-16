"""APScheduler — фоновые cron-задачи агента.

Три задачи:
1. check_inbox_job    — IMAP каждые 10 минут
2. send_queued_job    — отправка queued-писем с антиспам-задержками (каждые 5 мин)
3. follow_up_job      — автогенерация follow-up по next_action_at (каждые 30 мин)

Запуск/остановка управляются через lifespan FastAPI (main.py).
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import select, and_

from backend.config import settings
from backend.database import SessionLocal
from backend.models.lead import Lead, LeadStatus
from backend.models.message import Message, MessageDirection, MessageStatus

log = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


# ==========================
# Job 1: Проверка входящих
# ==========================
def check_inbox_job() -> None:
    """Забирает UNSEEN-письма из IMAP и привязывает к лидам."""
    log.info("[scheduler] check_inbox_job: старт")
    from backend.services.email_reader import fetch_new_messages, EmailReadError

    with SessionLocal() as db:
        try:
            summary = fetch_new_messages(db)
            log.info(
                "[scheduler] check_inbox_job: checked=%d, matched=%d, saved=%d",
                summary.checked,
                summary.matched,
                len(summary.saved_messages),
            )
        except EmailReadError as exc:
            log.error("[scheduler] IMAP ошибка: %s", exc)


# ==========================
# Job 2: Отправка queued-писем
# ==========================
def send_queued_job() -> None:
    """Берёт одно queued-письмо и отправляет через SMTP.

    Одно за раз — следующий вызов через 5 мин, что естественно даёт
    интервал между письмами. Если AUTO_SEND=false и письмо queued —
    значит его одобрили вручную через UI (approve), отправляем.
    """
    from backend.services.email_sender import send_email, EmailSendError
    from backend.services.antispam import under_daily_limit

    with SessionLocal() as db:
        if not under_daily_limit(db):
            log.info("[scheduler] send_queued: дневной лимит исчерпан — пропускаем")
            return

        # Берём самое старое queued-сообщение
        msg = db.execute(
            select(Message)
            .where(
                and_(
                    Message.direction == MessageDirection.outgoing,
                    Message.status == MessageStatus.queued,
                )
            )
            .order_by(Message.created_at.asc())
            .limit(1)
        ).scalar_one_or_none()

        if msg is None:
            return  # ничего в очереди

        lead = db.get(Lead, msg.lead_id)
        if lead is None:
            log.warning("[scheduler] Лид %s не найден для Message %s", msg.lead_id, msg.id)
            msg.status = MessageStatus.failed
            db.commit()
            return

        # Собираем threading-данные
        all_msgs = list(
            db.execute(
                select(Message)
                .where(Message.lead_id == lead.id)
                .order_by(Message.created_at)
            )
            .scalars()
            .all()
        )
        refs = [m.email_message_id for m in all_msgs if m.email_message_id and m.id != msg.id]

        try:
            result = send_email(
                to=lead.email,
                subject=msg.subject or "FITSIZ",
                body_text=msg.body_text or "",
                attachments=msg.attachments,
                in_reply_to=msg.in_reply_to,
                references=refs or None,
            )
        except EmailSendError as exc:
            log.error("[scheduler] SMTP ошибка для лида %s: %s", lead.company_name, exc)
            msg.status = MessageStatus.failed
            db.commit()
            return

        msg.email_message_id = result.message_id
        msg.status = MessageStatus.sent
        msg.sent_at = result.sent_at

        lead.last_contact_at = result.sent_at
        if lead.status == LeadStatus.new:
            lead.status = LeadStatus.contacted

        db.commit()
        log.info(
            "[scheduler] Отправлено queued-письмо → %s (%s)",
            lead.email,
            lead.company_name,
        )


# ==========================
# Job 3: Follow-up автогенерация
# ==========================
def follow_up_job() -> None:
    """Ищет лидов без ответа с next_action_at <= now.

    Генерирует follow-up через AI, сохраняет:
    - status=draft если AUTO_SEND=false
    - status=queued если AUTO_SEND=true

    Двигает lead.status на follow_up_1/2/3 и устанавливает next_action_at
    на следующий этап.
    """
    from backend.services.ai_engine import generate_follow_up, AIEngineError

    now = datetime.utcnow()

    with SessionLocal() as db:
        leads = list(
            db.execute(
                select(Lead)
                .where(
                    and_(
                        Lead.next_action_at <= now,
                        Lead.next_action_at.is_not(None),
                        Lead.status.in_([
                            LeadStatus.contacted,
                            LeadStatus.follow_up_1,
                            LeadStatus.follow_up_2,
                        ]),
                        Lead.assigned_to == "agent",
                    )
                )
                .limit(10)  # порциями, чтобы не перегружать
            )
            .scalars()
            .all()
        )

        if not leads:
            return

        log.info("[scheduler] follow_up_job: %d лидов нуждаются в follow-up", len(leads))

        for lead in leads:
            # Определяем стадию
            stage_map = {
                LeadStatus.contacted: "follow_up_1",
                LeadStatus.follow_up_1: "follow_up_2",
                LeadStatus.follow_up_2: "follow_up_3",
            }
            stage = stage_map.get(lead.status)
            if not stage:
                continue

            messages = list(
                db.execute(
                    select(Message)
                    .where(Message.lead_id == lead.id)
                    .order_by(Message.created_at)
                )
                .scalars()
                .all()
            )

            try:
                draft = generate_follow_up(lead, messages, stage)
            except AIEngineError as exc:
                log.error(
                    "[scheduler] AI ошибка для follow-up %s (%s): %s",
                    lead.company_name,
                    stage,
                    exc,
                )
                continue

            # Ищем in_reply_to — последний email_message_id из переписки
            anchor = None
            for m in reversed(messages):
                if m.email_message_id:
                    anchor = m.email_message_id
                    break

            # Статус черновика: зависит от AUTO_SEND
            msg_status = MessageStatus.queued if settings.auto_send else MessageStatus.draft

            msg = Message(
                lead_id=lead.id,
                direction=MessageDirection.outgoing,
                subject=draft.subject,
                body_text=draft.body_text,
                attachments=draft.attachments or None,
                in_reply_to=anchor,
                status=msg_status,
                ai_prompt_used=draft.ai_prompt_used,
                created_at=now,
            )
            db.add(msg)

            # Двигаем воронку
            lead.status = LeadStatus(stage)

            # Следующий follow-up
            next_delays = {
                "follow_up_1": timedelta(days=4),  # +4 дня до follow_up_2
                "follow_up_2": timedelta(days=7),  # +7 дней до follow_up_3
                "follow_up_3": None,                # финал, больше не пишем
            }
            next_delta = next_delays.get(stage)
            if next_delta:
                lead.next_action_at = now + next_delta
            else:
                lead.next_action_at = None  # follow_up_3 — конец цепочки

            db.commit()
            log.info(
                "[scheduler] Follow-up %s создан для %s (%s) → status=%s",
                stage,
                lead.company_name,
                msg_status.value,
                lead.status.value,
            )


# ==========================
# Управление
# ==========================
def start_scheduler() -> None:
    """Регистрирует и запускает все фоновые задачи."""
    interval_inbox = settings.inbox_check_interval_sec  # 600 = 10 мин

    scheduler.add_job(
        check_inbox_job,
        "interval",
        seconds=interval_inbox,
        id="check_inbox",
        replace_existing=True,
        max_instances=1,
    )
    scheduler.add_job(
        send_queued_job,
        "interval",
        seconds=300,  # каждые 5 мин
        id="send_queued",
        replace_existing=True,
        max_instances=1,
    )
    scheduler.add_job(
        follow_up_job,
        "interval",
        seconds=1800,  # каждые 30 мин
        id="follow_up",
        replace_existing=True,
        max_instances=1,
    )

    scheduler.start()
    log.info(
        "[scheduler] Запущен: inbox каждые %ds, queued каждые 300s, follow-up каждые 1800s",
        interval_inbox,
    )


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
        log.info("[scheduler] Остановлен")
