"""Передача лида живому менеджеру: бриф на проработку + полная переписка .txt.

Тема: «Новая компания на проработку — {Компания}». Тело собирается БЕЗ ссылок
на дашборд (у менеджера нет доступа). Контакты ЛПР и резюме переписки извлекает
AI; при сбое AI репорт всё равно уходит — с пометкой и вложением-перепиской.

Дедуп: повторный авто-репорт по лиду глушится 24ч; ручной клик идёт с force=True.
Аудит: каждый отправленный репорт сохраняется как Message(ai_prompt_used='manager_report').
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from backend.config import settings
from backend.models.lead import ColdStage, Lead, LeadStatus
from backend.models.message import Message, MessageDirection, MessageStatus
from backend.services.email_sender import EmailSendError, send_email

log = logging.getLogger(__name__)

REPORT_MARKER = "manager_report"


class NotifierError(RuntimeError):
    """Ошибка при отправке репорта менеджеру."""


# ==========================================
# Сборка письма
# ==========================================
def _subject(lead: Lead) -> str:
    return f"Новая компания на проработку — {lead.company_name}"


def _greeting() -> str:
    name = (settings.manager_name or "").strip()
    return f"Здравствуйте, {name}!" if name else "Здравствуйте!"


_TRANSLIT = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e",
    "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "h", "ц": "c", "ч": "ch", "ш": "sh", "щ": "sch", "ъ": "",
    "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
}


def _slug(text: str) -> str:
    out: list[str] = []
    for ch in (text or "").lower():
        if ch in _TRANSLIT:
            out.append(_TRANSLIT[ch])
        elif ch.isalnum() and ch.isascii():
            out.append(ch)
        else:
            out.append("_")
    slug = "".join(out).strip("_")
    while "__" in slug:
        slug = slug.replace("__", "_")
    return slug or "company"


def _who(direction: MessageDirection) -> str:
    return "FITSIZ" if direction == MessageDirection.outgoing else "Клиент"


def build_conversation_txt(lead: Lead, messages: list[Message]) -> tuple[str, str]:
    """Собирает (имя_файла, текст) полной переписки в читаемом .txt."""
    lines: list[str] = [
        f"Переписка с компанией: {lead.company_name}",
        f"Email лида: {lead.email}",
        "=" * 60,
        "",
    ]
    real = [m for m in messages if (m.ai_prompt_used or "") != REPORT_MARKER]
    if not real:
        lines.append("(сообщений ещё не было)")
    for m in real:
        when = (m.sent_at or m.created_at or datetime.utcnow()).strftime("%Y-%m-%d %H:%M")
        subj = f" — {m.subject}" if m.subject else ""
        lines.append(f"[{_who(m.direction)}] {when}{subj}")
        lines.append((m.body_text or "").strip() or "(пусто)")
        lines.append("")
        lines.append("-" * 60)
        lines.append("")
    filename = f"perepiska_{_slug(lead.company_name)}.txt"
    return filename, "\n".join(lines)


def _build_report_body(lead, brief, *, ai_ok: bool) -> str:
    parts: list[str] = [_greeting(), ""]

    # КОМПАНИЯ
    company_line = f"КОМПАНИЯ: {lead.company_name}"
    extra = ", ".join(x for x in (lead.city, lead.specialization) if x)
    if extra:
        company_line += f" ({extra})"
    parts.append(company_line)

    # КОНТАКТЫ ЛПР
    parts.append("")
    parts.append("КОНТАКТЫ ЛПР:")
    if ai_ok and brief is not None and brief.has_contacts():
        if brief.contact_name:
            pos = f", {brief.contact_position}" if brief.contact_position else ""
            parts.append(f"  ФИО: {brief.contact_name}{pos}")
        elif brief.contact_position:
            parts.append(f"  Должность: {brief.contact_position}")
        if brief.contact_phone:
            parts.append(f"  Телефон: {brief.contact_phone}")
        if brief.contact_email:
            parts.append(f"  Email: {brief.contact_email}")
    else:
        # fallback из карточки + email лида
        fallback = []
        if lead.contact_name:
            fallback.append(f"  ФИО (из карточки): {lead.contact_name}")
        if lead.phone:
            fallback.append(f"  Телефон (из карточки): {lead.phone}")
        fallback.append(f"  Email лида: {lead.email}")
        parts.extend(fallback)

    # О ЧЁМ ДОГОВОРИЛИСЬ
    parts.append("")
    parts.append("О ЧЁМ ДОГОВОРИЛИСЬ:")
    if ai_ok and brief is not None and brief.summary:
        parts.append(f"  {brief.summary}")
    else:
        parts.append(
            "  Резюме и контакты собрать автоматически не удалось — "
            "см. вложение с полной перепиской."
        )

    # ЗАДАЧА
    parts.append("")
    parts.append(
        "ЗАДАЧА: связаться с компанией по контактам выше, проработать "
        "сотрудничество. Полная переписка — во вложении (.txt)."
    )
    return "\n".join(parts)


# ==========================================
# Дедупликация
# ==========================================
def _already_notified_recently(db: Session, lead_id: str, hours: int = 24) -> bool:
    since = datetime.utcnow() - timedelta(hours=hours)
    stmt = (
        select(Message.id)
        .where(
            and_(
                Message.lead_id == lead_id,
                Message.ai_prompt_used == REPORT_MARKER,
                Message.created_at >= since,
            )
        )
        .limit(1)
    )
    return db.execute(stmt).scalar_one_or_none() is not None


# ==========================================
# Основная отправка репорта
# ==========================================
def send_manager_report(
    db: Session, lead: Lead, *, force: bool = False
) -> str | None:
    """Формирует и отправляет бриф менеджеру + переписку .txt.

    Возвращает Message.id аудит-записи или None (нет адресов / дедуп).
    AI-сбой НЕ роняет отправку — репорт уходит с пометкой.
    """
    from backend.services.app_settings import get_manager_emails

    recipients = get_manager_emails(db)
    if not recipients:
        log.warning("Список почт менеджеров пуст — репорт не отправлен")
        return None

    if not force and _already_notified_recently(db, lead.id):
        log.info("Репорт по лиду %s уже уходил за 24ч — пропускаем", lead.id)
        return None

    messages = sorted(lead.messages, key=lambda m: m.created_at)

    # --- AI: контакты + резюме. Сбой НЕ роняет передачу ---
    brief = None
    ai_ok = False
    try:
        from backend.services.ai_engine import build_manager_brief

        brief = build_manager_brief(lead, messages)
        ai_ok = True
    except Exception as exc:  # noqa: BLE001 — AIEngineError, сеть, ключ и пр.
        log.warning(
            "Репорт по лиду %s: AI-бриф не собран (%s) — шлём с пометкой",
            lead.id,
            exc,
        )

    subject = _subject(lead)
    body = _build_report_body(lead, brief, ai_ok=ai_ok)
    txt_name, txt_content = build_conversation_txt(lead, messages)

    try:
        result = send_email(
            to=", ".join(recipients),
            subject=subject,
            body_text=body,
            text_attachments=[(txt_name, txt_content)],
            append_signature=False,  # внутреннее письмо менеджеру, без cold-подписи/отписки
        )
    except EmailSendError as exc:
        log.error("Не удалось отправить репорт менеджеру: %s", exc)
        raise NotifierError(str(exc)) from exc

    audit = Message(
        lead_id=lead.id,
        direction=MessageDirection.outgoing,
        subject=subject,
        body_text=body,
        email_message_id=result.message_id,
        status=MessageStatus.sent,
        sent_at=result.sent_at,
        ai_prompt_used=REPORT_MARKER,
        created_at=datetime.utcnow(),
    )
    db.add(audit)
    db.commit()
    db.refresh(audit)

    log.info(
        "Репорт менеджерам %s по лиду %s (%s); AI=%s",
        ", ".join(recipients),
        lead.id,
        lead.company_name,
        "ok" if ai_ok else "fallback",
    )
    return audit.id


# ==========================================
# Передача менеджеру (статус + репорт) — единая точка
# ==========================================
def hand_off_to_manager(
    db: Session, lead: Lead, *, manager: str = "manager", force: bool = True
) -> str | None:
    """Переводит лид в handed_to_manager и отправляет бриф. Возвращает audit id."""
    lead.status = LeadStatus.handed_to_manager
    lead.cold_stage = None
    lead.next_action_at = None
    lead.assigned_to = manager
    db.commit()
    return send_manager_report(db, lead, force=force)


# ==========================================
# Тестовый репорт (для Settings UI)
# ==========================================
def send_test_manager_notification(db: Session) -> str:
    """Тестовый бриф на почты менеджеров с фиктивными данными."""
    from backend.services.app_settings import get_manager_emails

    recipients = get_manager_emails(db)
    if not recipients:
        raise NotifierError(
            "Список почт менеджеров пуст — добавьте хотя бы одну почту в Настройках"
        )

    subject = "Новая компания на проработку — Демо-компания (ТЕСТ)"
    body = (
        f"{_greeting()}\n\n"
        "КОМПАНИЯ: Демо-компания (Казань, сварочное оборудование)\n\n"
        "КОНТАКТЫ ЛПР:\n"
        "  ФИО: Иванов Сергей, закупщик\n"
        "  Телефон: +7 900 000-00-00\n"
        "  Email: test@example.com\n\n"
        "О ЧЁМ ДОГОВОРИЛИСЬ:\n"
        "  Запросил прайс и условия, готов обсуждать поставку, просил позвонить.\n\n"
        "ЗАДАЧА: связаться с компанией по контактам выше, проработать "
        "сотрудничество. Полная переписка — во вложении (.txt)."
    )
    try:
        result = send_email(
            to=", ".join(recipients),
            subject=subject,
            body_text=body,
            text_attachments=[("perepiska_demo.txt", "Демо-переписка для теста.")],
            append_signature=False,
        )
    except EmailSendError as exc:
        raise NotifierError(str(exc)) from exc

    return result.message_id
