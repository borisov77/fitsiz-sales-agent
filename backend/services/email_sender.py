"""SMTP-отправка через Mail.ru для бизнеса.

Отвечает за:
  - Сборку MIME-сообщения (plain + опционально HTML, вложения из документов).
  - Threading через In-Reply-To / References.
  - Подпись агента + ссылку "Отписаться" (List-Unsubscribe header + футер).
  - Передачу в smtp.mail.ru:465 (SSL).

Интеграция с моделями: возвращает `Message-ID` и время отправки,
а вызывающая сторона (scheduler / CRUD) сохраняет это в `Message`.
"""
from __future__ import annotations

import smtplib
import ssl
import uuid
from dataclasses import dataclass
from datetime import datetime
from email.message import EmailMessage
from email.utils import format_datetime, formataddr, make_msgid
from pathlib import Path

from backend.config import BASE_DIR, settings


# Каталог с вложениями (PDF-прайсы, каталоги, КП)
DOCUMENTS_DIR = BASE_DIR / "documents"


@dataclass
class SendResult:
    """Результат успешной SMTP-отправки."""

    message_id: str            # значение заголовка Message-ID
    sent_at: datetime          # UTC
    to: str
    subject: str


class EmailSendError(RuntimeError):
    """Любая ошибка на уровне SMTP/сборки письма."""


# ==========================
# Помощники
# ==========================
def _domain_from_address(addr: str) -> str:
    if "@" in addr:
        return addr.split("@", 1)[1]
    return "fitsiz.ru"


def _build_signature() -> str:
    """Подпись в plain-text (добавляется в конец тела)."""
    lines: list[str] = ["", "--"]
    name_line = settings.agent_name
    if settings.agent_title:
        name_line = f"{name_line}, {settings.agent_title}"
    lines.append(name_line)
    if settings.agent_phone:
        lines.append(settings.agent_phone)
    if settings.agent_signature:
        lines.append(settings.agent_signature)
    return "\n".join(lines)


def _build_unsubscribe_footer(lead_email: str) -> str:
    """Человекочитаемая инструкция по отписке внизу письма."""
    return (
        f"\n\nЕсли рассылка неактуальна — ответьте словом «отписаться»,\n"
        f"и мы больше не побеспокоим {lead_email}."
    )


def _compose_body(body_text: str, to_email: str) -> str:
    """Склеиваем тело + подпись + футер отписки."""
    signature = _build_signature()
    footer = _build_unsubscribe_footer(to_email)
    return f"{body_text.rstrip()}\n{signature}{footer}\n"


def _resolve_attachment_paths(attachments: list[str] | None) -> list[Path]:
    """Имена файлов → абсолютные пути внутри documents/. Проверяем существование."""
    if not attachments:
        return []
    resolved: list[Path] = []
    for name in attachments:
        # Защита: не позволяем выйти за documents/
        candidate = (DOCUMENTS_DIR / Path(name).name).resolve()
        if not candidate.is_file():
            raise EmailSendError(
                f"Вложение не найдено: {name} (ожидалось в documents/)"
            )
        resolved.append(candidate)
    return resolved


# Явная карта MIME для документов агента — почтовые клиенты показывают
# правильную иконку и открывают файл нужным приложением.
_MIME_BY_EXT: dict[str, tuple[str, str]] = {
    ".pdf": ("application", "pdf"),
    ".xlsx": (
        "application",
        "vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ),
    ".xls": ("application", "vnd.ms-excel"),
}


def _attach_file(msg: EmailMessage, path: Path) -> None:
    data = path.read_bytes()
    maintype, subtype = _MIME_BY_EXT.get(
        path.suffix.lower(), ("application", "octet-stream")
    )
    msg.add_attachment(
        data,
        maintype=maintype,
        subtype=subtype,
        filename=path.name,
    )


# ==========================
# Публичный API
# ==========================
def build_message(
    to: str,
    subject: str,
    body_text: str,
    *,
    attachments: list[str] | None = None,
    in_reply_to: str | None = None,
    references: list[str] | None = None,
) -> EmailMessage:
    """Собирает EmailMessage целиком (без отправки). Выделено для тестов."""
    if not settings.email_address:
        raise EmailSendError("EMAIL_ADDRESS не задан в .env")

    msg = EmailMessage()
    from_name = settings.agent_name or "FITSIZ"
    msg["From"] = formataddr((from_name, settings.email_address))
    msg["To"] = to
    msg["Subject"] = subject
    msg["Date"] = format_datetime(datetime.utcnow())
    msg["Message-ID"] = make_msgid(domain=_domain_from_address(settings.email_address))

    # Threading: если отвечаем в существующую цепочку
    if in_reply_to:
        msg["In-Reply-To"] = in_reply_to
        refs = list(references or [])
        if in_reply_to not in refs:
            refs.append(in_reply_to)
        if refs:
            msg["References"] = " ".join(refs)

    # List-Unsubscribe (RFC 2369) — снижает попадание в спам
    msg["List-Unsubscribe"] = (
        f"<mailto:{settings.email_address}?subject=Unsubscribe>"
    )
    msg["List-Unsubscribe-Post"] = "List-Unsubscribe=One-Click"

    body = _compose_body(body_text, to)
    msg.set_content(body, subtype="plain", charset="utf-8")

    # Вложения
    for path in _resolve_attachment_paths(attachments):
        _attach_file(msg, path)

    return msg


def send_email(
    to: str,
    subject: str,
    body_text: str,
    *,
    attachments: list[str] | None = None,
    in_reply_to: str | None = None,
    references: list[str] | None = None,
    timeout: float = 30.0,
) -> SendResult:
    """Отправка письма через SMTP Mail.ru (SSL).

    Вложения передаются как имена файлов внутри каталога `documents/`.
    Возвращает `SendResult` с `Message-ID` для дальнейшего threading.
    """
    msg = build_message(
        to=to,
        subject=subject,
        body_text=body_text,
        attachments=attachments,
        in_reply_to=in_reply_to,
        references=references,
    )

    if not settings.email_password:
        raise EmailSendError("EMAIL_PASSWORD не задан в .env")

    context = ssl.create_default_context()
    try:
        with smtplib.SMTP_SSL(
            host=settings.smtp_host,
            port=settings.smtp_port,
            context=context,
            timeout=timeout,
        ) as smtp:
            smtp.login(settings.email_address, settings.email_password)
            smtp.send_message(msg)
    except (smtplib.SMTPException, OSError) as exc:
        raise EmailSendError(f"SMTP ошибка: {exc}") from exc

    # Некоторые MTA переписывают Message-ID; логируем то, что ушло.
    message_id = msg["Message-ID"] or f"<{uuid.uuid4()}@fitsiz.ru>"
    return SendResult(
        message_id=message_id,
        sent_at=datetime.utcnow(),
        to=to,
        subject=subject,
    )
