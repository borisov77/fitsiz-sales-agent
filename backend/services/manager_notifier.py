"""Уведомление менеджеру по email при warm-лиде.

Триггер: lead.status → warm (intent=ready / is_warm=true).
Отправляется через тот же SMTP-канал (email_sender), но на адрес MANAGER_EMAIL.
Deep-link ведёт в dashboard: {PUBLIC_BASE_URL}/conversations/{lead.id}.

Дедупликация: не шлём повторно, если менеджеру уже уходил warm-alert
по этому лиду в последние 24 часа (проверяем по Message с
ai_prompt_used='manager_notification').
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

from sqlalchemy import select, and_
from sqlalchemy.orm import Session

from backend.config import settings
from backend.models.lead import Lead
from backend.models.message import Message, MessageDirection, MessageStatus
from backend.services.email_sender import EmailSendError, send_email

log = logging.getLogger(__name__)


class NotifierError(RuntimeError):
    """Ошибка при отправке уведомления."""


# ==========================================
# Сборка письма (без AI — шаблонный текст)
# ==========================================
def _build_subject(lead: Lead) -> str:
    city = lead.city or "—"
    return f"[warm] {lead.company_name}, {city} — готов обсуждать"


def _build_body(
    lead: Lead,
    *,
    last_incoming_text: str | None = None,
    qualifier: dict | None = None,
) -> str:
    """Собираем тело уведомления менеджеру. Без AI — быстро и предсказуемо."""
    link = f"{settings.public_base_url}/conversations/{lead.id}"
    parts: list[str] = []

    # 1. Кто
    line1 = f"{lead.company_name}"
    if lead.city:
        line1 += f", {lead.city}"
    if lead.specialization:
        line1 += f" ({lead.specialization})"
    parts.append(line1)

    # 2. Контакт
    contact = lead.contact_name or "—"
    email = lead.email
    phone = f", тел: {lead.phone}" if lead.phone else ""
    parts.append(f"Контакт: {contact}, {email}{phone}")

    # 3. Что написал клиент
    if last_incoming_text:
        snippet = last_incoming_text.strip()
        if len(snippet) > 500:
            snippet = snippet[:500] + "…"
        parts.append(f"Последнее сообщение клиента:\n{snippet}")

    # 4. Оценка AI (если есть)
    if qualifier:
        qi = qualifier.get("interest_score", "?")
        qb = qualifier.get("buying_readiness", "?")
        qv = qualifier.get("estimated_volume", "?")
        qna = qualifier.get("next_action", "—")
        parts.append(
            f"Оценка AI: интерес {qi}/10, готовность {qb}/10, "
            f"объём: {qv}"
        )
        parts.append(f"Рекомендация AI: {qna}")

    # 5. Ссылка
    parts.append(f"Переписка: {link}")

    return "\n\n".join(parts)


# ==========================================
# Дедупликация
# ==========================================
def _already_notified_recently(db: Session, lead_id: str, hours: int = 24) -> bool:
    """Проверяем, был ли warm-alert по этому лиду в последние N часов."""
    since = datetime.utcnow() - timedelta(hours=hours)
    stmt = (
        select(Message.id)
        .where(
            and_(
                Message.lead_id == lead_id,
                Message.ai_prompt_used == "manager_notification",
                Message.created_at >= since,
            )
        )
        .limit(1)
    )
    return db.execute(stmt).scalar_one_or_none() is not None


# ==========================================
# Основная функция
# ==========================================
def notify_manager_about_warm_lead(
    db: Session,
    lead: Lead,
    *,
    last_incoming_text: str | None = None,
    qualifier: dict | None = None,
    force: bool = False,
) -> str | None:
    """Отправляет уведомление менеджеру о тёплом лиде.

    Возвращает Message.id записи в БД (для аудита) или None если не отправлено
    (нет MANAGER_EMAIL или уже отправлялось недавно).
    """
    from backend.services.app_settings import get_manager_emails

    recipients = get_manager_emails(db)
    if not recipients:
        log.warning("Список почт менеджеров пуст — уведомление не отправлено")
        return None

    if not force and _already_notified_recently(db, lead.id):
        log.info(
            "Warm-alert по лиду %s уже отправлялся менеджеру в последние 24ч — пропускаем",
            lead.id,
        )
        return None

    subject = _build_subject(lead)
    body = _build_body(
        lead,
        last_incoming_text=last_incoming_text,
        qualifier=qualifier,
    )

    # Шлём одно письмо на все адреса менеджеров (в заголовке To — все).
    try:
        result = send_email(
            to=", ".join(recipients),
            subject=subject,
            body_text=body,
        )
    except EmailSendError as exc:
        log.error("Не удалось отправить warm-alert: %s", exc)
        raise NotifierError(str(exc)) from exc

    # Сохраняем как internal-message для аудита (lead_id — к какому лиду)
    msg = Message(
        lead_id=lead.id,
        direction=MessageDirection.outgoing,
        subject=subject,
        body_text=body,
        email_message_id=result.message_id,
        status=MessageStatus.sent,
        sent_at=result.sent_at,
        ai_prompt_used="manager_notification",
        created_at=datetime.utcnow(),
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)

    log.info(
        "Warm-alert отправлен менеджерам %s по лиду %s (%s)",
        ", ".join(recipients),
        lead.id,
        lead.company_name,
    )
    return msg.id


# ==========================================
# Тестовый warm-alert (для Settings UI)
# ==========================================
def send_test_manager_notification(db: Session) -> str:
    """Отправляет тестовый warm-alert на MANAGER_EMAIL с фиктивным лидом.
    Возвращает Message-ID smtp-письма.
    """
    from backend.services.app_settings import get_manager_emails

    recipients = get_manager_emails(db)
    if not recipients:
        raise NotifierError("Список почт менеджеров пуст — добавьте хотя бы одну почту в Настройках")

    subject = "[warm][ТЕСТ] Демо-компания, Казань — тестовое уведомление"
    body = (
        "Демо-компания, Казань (сварочное оборудование, СИЗ)\n\n"
        f"Контакт: Иванов Сергей, test@example.com\n\n"
        "Последнее сообщение клиента:\n"
        "Добрый день! Готовы обсуждать поставку, пришлите проект договора.\n\n"
        "Оценка AI: интерес 9/10, готовность 8/10, объём: medium\n\n"
        "Рекомендация AI: передать менеджеру, подготовить КП\n\n"
        f"Переписка: {settings.public_base_url}/conversations/test-demo-id"
    )

    try:
        result = send_email(
            to=", ".join(recipients),
            subject=subject,
            body_text=body,
        )
    except EmailSendError as exc:
        raise NotifierError(str(exc)) from exc

    return result.message_id
