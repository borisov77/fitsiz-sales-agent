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
    from backend.services.antispam import under_daily_limit, random_cold_delay_sec
    from backend.services.app_settings import (
        get_next_cold_send_at,
        set_next_cold_send_at,
    )
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
        if lead.status == LeadStatus.new:
            lead.status = LeadStatus.contacted

        # Зона 1: отправили ПЕРВОЕ (cold) письмо → планируем напоминание через 1 день.
        # Это и есть фикс бага, из-за которого next_action_at оставался None
        # и follow_up_job никогда не срабатывал. Для напоминания и диалоговых
        # писем next_action_at тут НЕ трогаем (им управляет follow_up_job / приём).
        if msg.ai_prompt_used == COLD_TEMPLATE_MARKER:
            lead.next_action_at = result.sent_at + timedelta(days=1)

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
    """Зона 1 (холодный автомат): ОДНО напоминание-шаблон, затем dead_email.

    Без AI. Два перехода по `next_action_at`:
      - `contacted` + срок наступил (1 день тишины) → ставим в очередь ОДНО
        напоминание из ШАБЛОНА (status=queued, НЕЗАВИСИМО от AUTO_SEND),
        статус → `follow_up_1`, next_action_at = +4 дня.
      - `follow_up_1` + срок наступил (ещё 4 дня, итого 5 тишины) → больше
        НЕ пишем: статус → `dead_email`, next_action_at = None.

    Диалоговых лидов (replied/interested/negotiating) сюда не берём — они
    не входят в фильтр статусов и выходят из холодной автоматики.
    """
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
                        Lead.status.in_([
                            LeadStatus.contacted,
                            LeadStatus.follow_up_1,
                        ]),
                        Lead.assigned_to == "agent",
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
            # --- Переход 2: follow_up_1 → dead_email (5 дней тишины) ---
            if lead.status == LeadStatus.follow_up_1:
                lead.status = LeadStatus.dead_email
                lead.next_action_at = None
                db.commit()
                log.info(
                    "[scheduler] follow_up: %s (%s) → dead_email (5 дней тишины)",
                    lead.id,
                    lead.company_name,
                )
                continue

            # --- Переход 1: contacted → одно напоминание из шаблона ---
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

            lead.status = LeadStatus.follow_up_1
            lead.next_action_at = now + timedelta(days=4)

            db.commit()
            log.info(
                "[scheduler] follow_up: напоминание → очередь для %s (%s); "
                "dead_email через 4 дня без ответа",
                lead.id,
                lead.company_name,
            )


# ==========================
# Job 4: Авто-черновик ответа на входящее (Зона 2)
# ==========================
# Метки результата на ВХОДЯЩЕМ письме (поле Message.ai_prompt_used).
# Колонка уже существует — отдельной миграции БД не требуется.
AUTODRAFT_DONE = "autodraft:done"        # черновик создан → больше не трогаем
AUTODRAFT_SILENT = "autodraft:silent"    # AI решил молчать → больше не трогаем
AUTODRAFT_ERR_PREFIX = "autodraft:err:"  # "autodraft:err:N" — N неудачных попыток
AUTODRAFT_MAX_RETRIES = 3                 # после N сбоев — оставляем человеку


def auto_draft_reply_job() -> None:
    """Зона 2 (диалог): на НОВОЕ входящее генерим ЧЕРНОВИК ответа через AI.

    Отдельная задача — НЕ внутри email_reader: сбой AI (нет ключа, таймаут)
    здесь никогда не затронет IMAP-приём писем. Приём важнее генерации.

    Черновик ВСЕГДА status=draft (НЕ зависит от AUTO_SEND) — диалоговый поток
    гейтит человек кнопкой в дашборде. Статус лида тут НЕ двигаем.

    Защита от холостых перегенераций: КАЖДОЕ обработанное входящее помечается
    на самом письме (Message.ai_prompt_used) — done / silent / err:N. Запрос
    исключает уже терминально помеченные, поэтому AI вызывается РОВНО один раз
    на каждое новое входящее (а при ошибке — не более AUTODRAFT_MAX_RETRIES).
    """
    from backend.services.ai_engine import handle_reply

    DIALOG_BUCKET = [
        LeadStatus.replied,
        LeadStatus.interested,
        LeadStatus.negotiating,
    ]
    # Терминальные метки — такие входящие AI больше не трогает
    TERMINAL = (AUTODRAFT_DONE, AUTODRAFT_SILENT, "detected:autoreply")

    with SessionLocal() as db:
        leads = list(
            db.execute(
                select(Lead)
                .where(
                    and_(
                        Lead.status.in_(DIALOG_BUCKET),
                        Lead.assigned_to == "agent",
                    )
                )
                .limit(20)
            )
            .scalars()
            .all()
        )

        for lead in leads:
            msgs = list(
                db.execute(
                    select(Message)
                    .where(Message.lead_id == lead.id)
                    .order_by(Message.created_at)
                )
                .scalars()
                .all()
            )

            incomings = [
                m for m in msgs if m.direction == MessageDirection.incoming
            ]
            if not incomings:
                continue
            last_incoming = incomings[-1]
            mark = last_incoming.ai_prompt_used or ""

            # Уже обработано терминально (черновик/молчание/автоответчик) — пропуск
            if mark in TERMINAL:
                continue

            # Исчерпан ретрай-кап по ошибкам — оставляем лид человеку
            if mark.startswith(AUTODRAFT_ERR_PREFIX):
                try:
                    attempts = int(mark[len(AUTODRAFT_ERR_PREFIX):])
                except ValueError:
                    attempts = 0
                if attempts >= AUTODRAFT_MAX_RETRIES:
                    continue
            else:
                attempts = 0

            # Бэкап-страж: на это входящее уже ответили (человек/прошлый прогон) —
            # помечаем done и не зовём AI.
            already = any(
                m.direction == MessageDirection.outgoing
                and m.created_at >= last_incoming.created_at
                for m in msgs
            )
            if already:
                last_incoming.ai_prompt_used = AUTODRAFT_DONE
                db.commit()
                continue

            # --- Генерация. Любой сбой AI НЕ роняет задачу (per-lead) ---
            try:
                draft = handle_reply(lead, msgs, last_incoming)
            except Exception as exc:  # noqa: BLE001 — AIEngineError и прочее
                # ВРЕМЕННЫЙ сбой: инкрементируем счётчик, но не метим навсегда.
                attempts += 1
                last_incoming.ai_prompt_used = f"{AUTODRAFT_ERR_PREFIX}{attempts}"
                db.commit()
                log.error(
                    "[scheduler] auto_draft: AI-сбой для %s (%s), попытка %d/%d — "
                    "входящее принято, черновик не создан: %s",
                    lead.id,
                    lead.company_name,
                    attempts,
                    AUTODRAFT_MAX_RETRIES,
                    exc,
                )
                continue

            # AI решил промолчать — метим НАВСЕГДА, повторно не дёргаем
            if not draft.should_send:
                last_incoming.ai_prompt_used = AUTODRAFT_SILENT
                db.commit()
                log.info(
                    "[scheduler] auto_draft: AI рекомендует молчать (intent=%s) — "
                    "лид %s, помечено silent",
                    draft.intent,
                    lead.id,
                )
                continue

            # ВСЕГДА draft — человек решит отправить/править/квалифицировать.
            # Статус лида НЕ трогаем: остаётся в диалоговом бакете.
            reply = Message(
                lead_id=lead.id,
                direction=MessageDirection.outgoing,
                subject=draft.subject,
                body_text=draft.body_text,
                attachments=draft.attachments or None,
                in_reply_to=last_incoming.email_message_id,
                status=MessageStatus.draft,
                ai_prompt_used=f"reply_handler:auto:intent={draft.intent}",
                created_at=datetime.utcnow(),
            )
            db.add(reply)
            last_incoming.ai_prompt_used = AUTODRAFT_DONE  # метим обработанным
            db.commit()
            log.info(
                "[scheduler] auto_draft: черновик ответа создан для %s (%s), intent=%s",
                lead.id,
                lead.company_name,
                draft.intent,
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
    scheduler.add_job(
        auto_draft_reply_job,
        "interval",
        seconds=600,  # Зона 2: не чаще приёма почты (check_inbox=600s)
        id="auto_draft_reply",
        replace_existing=True,
        max_instances=1,
    )

    scheduler.start()
    log.info(
        "[scheduler] Запущен: inbox %ds, queued 60s, follow-up 1800s, auto-draft 600s",
        interval_inbox,
    )


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
        log.info("[scheduler] Остановлен")
