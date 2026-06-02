"""IMAP-чтение входящих через imapclient.

Подключается к imap.mail.ru:993 (SSL), забирает UNSEEN-письма, парсит,
привязывает к лидам (по From email), сохраняет как `Message(incoming)`.
Помечает обработанные письма как прочитанные.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from imapclient import IMAPClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.config import settings
from backend.models.lead import Lead, LeadStatus
from backend.models.message import Message, MessageDirection, MessageStatus
from backend.services.email_parser import ParsedEmail, parse


@dataclass
class FetchSummary:
    """Что случилось за один цикл проверки входящих."""

    checked: int = 0                 # всего UNSEEN-писем
    matched: int = 0                 # привязаны к лиду
    unmatched: int = 0               # от неизвестного email
    saved_messages: list[str] = field(default_factory=list)  # ids сохранённых Message
    updated_leads: list[str] = field(default_factory=list)   # ids лидов


class EmailReadError(RuntimeError):
    """Ошибка IMAP-подключения или парсинга."""


# ==========================
# Работа с лидами
# ==========================
def _find_lead_by_email(db: Session, address: str) -> Lead | None:
    if not address:
        return None
    return db.execute(
        select(Lead).where(Lead.email == address.lower())
    ).scalar_one_or_none()


def _is_autoreply(parsed: ParsedEmail, headers: dict[str, Any]) -> bool:
    """Грубое определение автоответчика (out-of-office, уведомления)."""
    subj = (parsed.subject or "").lower()
    autoreply_markers = (
        "out of office",
        "автоответ",
        "я в отпуске",
        "away from office",
        "vacation",
    )
    if any(m in subj for m in autoreply_markers):
        return True
    # RFC-заголовки автоответчиков
    for h in ("Auto-Submitted", "X-Autorespond", "X-Autoreply", "Precedence"):
        val = headers.get(h)
        if val and str(val).lower() not in ("", "no"):
            if h == "Precedence" and str(val).lower() in ("bulk", "auto_reply"):
                return True
            if h != "Precedence":
                return True
    return False


def _save_incoming(
    db: Session,
    lead: Lead,
    parsed: ParsedEmail,
) -> Message:
    """Сохраняет одно входящее в `messages`. Обновляет last_contact_at лида."""
    msg = Message(
        lead_id=lead.id,
        direction=MessageDirection.incoming,
        subject=parsed.subject or None,
        body_text=parsed.body_text_clean or parsed.body_text or "",
        body_html=parsed.body_html,
        email_message_id=parsed.message_id,
        in_reply_to=parsed.in_reply_to,
        status=MessageStatus.received,
        created_at=datetime.utcnow(),
    )
    db.add(msg)

    # Обновляем состояние лида
    lead.last_contact_at = datetime.utcnow()
    # Первый реальный ответ: статус → replied (если лид ещё в холодной зоне).
    # dead_email включён намеренно: «мёртвый» лид, который вдруг ответил,
    # должен подняться обратно в диалог, а не остаться в архиве.
    transitions = {
        LeadStatus.new,
        LeadStatus.contacted,
        LeadStatus.follow_up_1,
        LeadStatus.follow_up_2,
        LeadStatus.follow_up_3,
        LeadStatus.dead_email,
    }
    if lead.status in transitions:
        lead.status = LeadStatus.replied
    # Сбрасываем плановое следующее действие — AI обработает свежий ответ
    lead.next_action_at = None

    db.flush()
    return msg


# ==========================
# Основной цикл
# ==========================
def fetch_new_messages(
    db: Session,
    folder: str = "INBOX",
    mark_as_seen: bool = True,
    limit: int | None = None,
) -> FetchSummary:
    """Забирает UNSEEN-письма из INBOX и сохраняет те, что от известных лидов.

    Возвращает сводку. Письма, не привязанные к лидам, остаются непрочитанными —
    чтобы человек мог вручную обработать их через веб-клиент.
    """
    if not settings.email_address or not settings.email_password:
        raise EmailReadError("EMAIL_ADDRESS / EMAIL_PASSWORD не заданы в .env")

    summary = FetchSummary()

    try:
        with IMAPClient(
            host=settings.imap_host,
            port=settings.imap_port,
            ssl=True,
            timeout=30,
        ) as client:
            client.login(settings.email_address, settings.email_password)
            client.select_folder(folder, readonly=False)

            uids = client.search(["UNSEEN"]) or []
            if limit is not None:
                uids = uids[:limit]

            summary.checked = len(uids)
            if not uids:
                return summary

            # Забираем raw-контент и все заголовки разом
            fetched = client.fetch(uids, ["RFC822", "ENVELOPE"])

            matched_uids: list[int] = []
            for uid, data in fetched.items():
                raw = data.get(b"RFC822")
                if not raw:
                    continue

                parsed = parse(raw)

                # Заголовки для детектора автоответа — через email.message_from_bytes
                headers_proxy: dict[str, Any] = {}
                msg_obj = _safe_parse(raw)
                if msg_obj is not None:
                    for key in (
                        "Auto-Submitted",
                        "X-Autorespond",
                        "X-Autoreply",
                        "Precedence",
                    ):
                        val = msg_obj.get(key)
                        if val:
                            headers_proxy[key] = val

                lead = _find_lead_by_email(db, parsed.from_address)
                if lead is None:
                    summary.unmatched += 1
                    continue

                # Автоответ — не двигаем воронку, но сохраняем как входящее
                if _is_autoreply(parsed, headers_proxy):
                    message = Message(
                        lead_id=lead.id,
                        direction=MessageDirection.incoming,
                        subject=parsed.subject or None,
                        body_text=parsed.body_text_clean
                        or parsed.body_text
                        or "[autoreply]",
                        email_message_id=parsed.message_id,
                        in_reply_to=parsed.in_reply_to,
                        status=MessageStatus.received,
                        ai_prompt_used="detected:autoreply",
                        created_at=datetime.utcnow(),
                    )
                    db.add(message)
                    db.flush()
                    summary.saved_messages.append(message.id)
                    matched_uids.append(uid)
                    summary.matched += 1
                    continue

                message = _save_incoming(db, lead, parsed)
                summary.saved_messages.append(message.id)
                if lead.id not in summary.updated_leads:
                    summary.updated_leads.append(lead.id)
                matched_uids.append(uid)
                summary.matched += 1

            if matched_uids and mark_as_seen:
                client.add_flags(matched_uids, [b"\\Seen"])

            db.commit()
    except EmailReadError:
        raise
    except Exception as exc:  # pragma: no cover
        db.rollback()
        raise EmailReadError(f"IMAP ошибка: {exc}") from exc

    return summary


def _safe_parse(raw: bytes):
    try:
        from backend.services.email_parser import parse_bytes

        return parse_bytes(raw)
    except Exception:
        return None
