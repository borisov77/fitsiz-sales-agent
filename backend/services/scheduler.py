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
from backend.models.lead import ColdStage, Lead, LeadStatus
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
    from backend.services.antispam import under_daily_limit, random_cold_delay_sec
    from backend.services.app_settings import (
        get_next_cold_send_at,
        set_next_cold_send_at,
    )
    from backend.services.app_settings import get_reminder_delay_days
    from backend.services.cold_template import (
        COLD_REMINDER_MARKER,
        COLD_TEMPLATE_MARKER,
    )

    with SessionLocal() as db:
        if not under_daily_limit(db):
            log.info("[scheduler] send_queued: дневной лимит исчерпан — пропускаем")
            return

        # Антиспам: не отправляем раньше запланированного момента (рандом 3-7 мин)
        next_at = get_next_cold_send_at(db)
        if next_at is not None and datetime.utcnow() < next_at:
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
                # cold-письмо и напоминание несут свою подпись — авто не добавляем
                append_signature=msg.ai_prompt_used
                not in (COLD_TEMPLATE_MARKER, COLD_REMINDER_MARKER),
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
        if lead.status == LeadStatus.created:
            lead.status = LeadStatus.sent

        # Зона 1: отправили ПЕРВОЕ (cold) письмо → входим в холодный автомат:
        # cold_stage=awaiting_reply, через REMINDER_DELAY_DAYS follow_up_job
        # отправит напоминание. Для напоминания и диалоговых писем next_action_at
        # тут НЕ трогаем (им управляет follow_up_job / приём почты).
        if msg.ai_prompt_used == COLD_TEMPLATE_MARKER:
            lead.cold_stage = ColdStage.awaiting_reply
            lead.next_action_at = result.sent_at + timedelta(
                days=get_reminder_delay_days(db)
            )

        # Планируем следующую отправку через рандомные 3-7 минут (антиспам)
        set_next_cold_send_at(
            db, result.sent_at + timedelta(seconds=random_cold_delay_sec())
        )

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
    """Зона 1 (холодный автомат): ОДНО напоминание-шаблон, затем no_reply.

    Без AI. Гейт строго по `status==sent` + `cold_stage`. Два перехода по
    `next_action_at`:
      - `sent` + `cold_stage=awaiting_reply` + срок (REMINDER_DELAY_DAYS) →
        ставим в очередь ОДНО напоминание из ШАБЛОНА (status=queued, НЕЗАВИСИМО
        от AUTO_SEND), `cold_stage=reminder_sent`, next_action_at = +NO_REPLY_DAYS.
      - `sent` + `cold_stage=reminder_sent` + срок (NO_REPLY_DAYS) → больше
        НЕ пишем: статус → `no_reply`, cold_stage=None, next_action_at=None.

    Диалоговые/закрытые лиды (in_dialog/handed_to_manager/won/lost/no_reply)
    сюда не попадают — они вне выборки `status==sent`.
    """
    from backend.services.app_settings import get_no_reply_days
    from backend.services.cold_template import (
        COLD_REMINDER_MARKER,
        ColdTemplateError,
        build_reminder_email,
        is_reminder_filled,
    )

    now = datetime.utcnow()

    with SessionLocal() as db:
        leads = list(
            db.execute(
                select(Lead)
                .where(
                    and_(
                        Lead.next_action_at.is_not(None),
                        Lead.next_action_at <= now,
                        Lead.status == LeadStatus.sent,
                    )
                )
                .limit(20)  # порциями, чтобы не перегружать
            )
            .scalars()
            .all()
        )

        if not leads:
            return

        log.info("[scheduler] follow_up_job: %d лид(ов) к обработке", len(leads))

        for lead in leads:
            # --- Переход 2: reminder_sent → no_reply (тишина после напоминания) ---
            if lead.cold_stage == ColdStage.reminder_sent:
                lead.status = LeadStatus.no_reply
                lead.cold_stage = None
                lead.next_action_at = None
                db.commit()
                log.info(
                    "[scheduler] follow_up: %s (%s) → no_reply (нет ответа)",
                    lead.id,
                    lead.company_name,
                )
                continue

            # --- Переход 1: awaiting_reply → одно напоминание из шаблона ---
            if not is_reminder_filled(db):
                # Без текста напоминания ничего не шлём и НЕ двигаем статус —
                # лид дождётся, когда шаблон заполнят в Настройках.
                log.warning(
                    "[scheduler] follow_up: шаблон напоминания пуст — лид %s пропущен",
                    lead.id,
                )
                continue

            try:
                subject, body = build_reminder_email(db, lead)
            except ColdTemplateError as exc:
                log.warning("[scheduler] follow_up: %s (лид %s)", exc, lead.id)
                continue

            # in_reply_to — последнее ОТПРАВЛЕННОЕ нами письмо (cold), для threading
            anchor = None
            msgs = list(
                db.execute(
                    select(Message)
                    .where(Message.lead_id == lead.id)
                    .order_by(Message.created_at)
                )
                .scalars()
                .all()
            )
            for m in reversed(msgs):
                if (
                    m.direction == MessageDirection.outgoing
                    and m.email_message_id
                ):
                    anchor = m.email_message_id
                    break

            # КРИТИЧНО: напоминание всегда queued — уходит автоматически,
            # НЕЗАВИСИМО от глобального AUTO_SEND. Это поток Зоны 1.
            reminder = Message(
                lead_id=lead.id,
                direction=MessageDirection.outgoing,
                subject=subject,
                body_text=body,
                in_reply_to=anchor,
                status=MessageStatus.queued,
                ai_prompt_used=COLD_REMINDER_MARKER,
                created_at=now,
            )
            db.add(reminder)

            no_reply_days = get_no_reply_days(db)
            lead.cold_stage = ColdStage.reminder_sent
            lead.next_action_at = now + timedelta(days=no_reply_days)

            db.commit()
            log.info(
                "[scheduler] follow_up: напоминание → очередь для %s (%s); "
                "no_reply через %d дн. без ответа",
                lead.id,
                lead.company_name,
                no_reply_days,
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
        seconds=60,  # проверяем очередь каждую минуту; отправку гейтит
        id="send_queued",  # next_cold_send_at (рандом 3-7 мин между письмами)
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
    # ВАЖНО: авто-черновик ответа (Зона 2) ОТКЛЮЧЁН намеренно. Диалоговые ответы
    # генерятся СТРОГО вручную — по кнопке «Ответить AI» (POST /draft-reply).
    # Это исключает холостые AI-вызовы на каждое входящее (утечка токенов).

    scheduler.start()
    log.info(
        "[scheduler] Запущен: inbox %ds, queued 60s, follow-up 1800s "
        "(auto-draft ОТКЛЮЧЁН — диалог только вручную)",
        interval_inbox,
    )


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
        log.info("[scheduler] Остановлен")
