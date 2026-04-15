"""Парсинг сырых email-сообщений: адреса, тема, текст, очистка цитат.

Вынесено из email_reader.py — чтобы можно было покрыть тестами отдельно
от IMAP-подключения.
"""
from __future__ import annotations

import email
import re
from dataclasses import dataclass, field
from email import policy
from email.message import EmailMessage
from email.utils import getaddresses, parseaddr


@dataclass
class ParsedEmail:
    """Нормализованное представление входящего письма."""

    message_id: str | None
    in_reply_to: str | None
    references: list[str] = field(default_factory=list)
    from_address: str = ""
    from_name: str = ""
    to_addresses: list[str] = field(default_factory=list)
    subject: str = ""
    body_text: str = ""
    body_text_clean: str = ""
    body_html: str | None = None


# Маркеры начала процитированной части в ответе клиента
_QUOTE_HEADERS = [
    # Английские клиенты
    re.compile(r"^on\s.+wrote:\s*$", re.IGNORECASE),
    re.compile(r"^-----\s*original message\s*-----\s*$", re.IGNORECASE),
    re.compile(r"^from:\s.+", re.IGNORECASE),
    re.compile(r"^sent:\s.+", re.IGNORECASE),
    # Русские (Mail.ru, Yandex, Outlook RU)
    re.compile(r"^\s*\d{1,2}\.\d{1,2}\.\d{2,4}.*(писал|написал|пишет)", re.IGNORECASE),
    re.compile(r"^\s*\d{1,2}\s+\S+\s+\d{2,4}.*(писал|написал|пишет)", re.IGNORECASE),
    re.compile(r"^-----\s*исходное сообщение\s*-----\s*$", re.IGNORECASE),
    re.compile(r"^от:\s.+", re.IGNORECASE),
    re.compile(r"^кому:\s.+", re.IGNORECASE),
    re.compile(r"^отправлено:\s.+", re.IGNORECASE),
]

# Разделитель подписи по RFC — строка `-- ` (с пробелом)
_SIGNATURE_SEPARATOR = re.compile(r"^--\s*$")


def parse_bytes(raw: bytes) -> EmailMessage:
    """email.message_from_bytes, но с современной политикой EmailMessage."""
    return email.message_from_bytes(raw, policy=policy.default)  # type: ignore[return-value]


def _decode_part(part: EmailMessage) -> str:
    payload = part.get_content()
    if isinstance(payload, bytes):
        charset = part.get_content_charset() or "utf-8"
        try:
            return payload.decode(charset, errors="replace")
        except LookupError:
            return payload.decode("utf-8", errors="replace")
    return str(payload)


def _extract_bodies(msg: EmailMessage) -> tuple[str, str | None]:
    """Возвращаем (plain_text, html). Берём первый попавшийся text/plain."""
    plain_text = ""
    html_text: str | None = None

    if msg.is_multipart():
        for part in msg.walk():
            if part.is_multipart():
                continue
            if part.get_content_disposition() == "attachment":
                continue
            ctype = part.get_content_type()
            if ctype == "text/plain" and not plain_text:
                plain_text = _decode_part(part)
            elif ctype == "text/html" and html_text is None:
                html_text = _decode_part(part)
    else:
        ctype = msg.get_content_type()
        if ctype == "text/plain":
            plain_text = _decode_part(msg)
        elif ctype == "text/html":
            html_text = _decode_part(msg)

    # Если plain пустой, но есть HTML — грубо вырезаем теги как fallback
    if not plain_text and html_text:
        stripped = re.sub(r"<br\s*/?>", "\n", html_text, flags=re.IGNORECASE)
        stripped = re.sub(r"</p\s*>", "\n\n", stripped, flags=re.IGNORECASE)
        stripped = re.sub(r"<[^>]+>", "", stripped)
        plain_text = stripped

    return plain_text.strip(), html_text


def clean_reply_text(text: str) -> str:
    """Убираем процитированный исходник и подпись.

    Простые эвристики:
      1. Срезаем всё, начиная со строки-маркера цитирования
         ("On ... wrote:", "От: ...", "20.03.2026 ... писал:" и т.п.)
      2. Срезаем блоки из последовательных строк, начинающихся с `>`.
      3. Срезаем всё после разделителя подписи `-- `.
    Результат — текст собственно ответа клиента.
    """
    if not text:
        return ""

    lines = text.splitlines()
    kept: list[str] = []
    consecutive_quoted = 0

    for line in lines:
        stripped = line.strip()

        # 1. Заголовок цитируемого исходника
        if any(rx.match(stripped) for rx in _QUOTE_HEADERS):
            break

        # 3. Разделитель подписи
        if _SIGNATURE_SEPARATOR.match(line):
            break

        # 2. Подряд идущие цитаты через `>`
        if stripped.startswith(">"):
            consecutive_quoted += 1
            # 2+ подряд — считаем, что пошёл блок цитирования, дальше не читаем
            if consecutive_quoted >= 2:
                # откатим последнюю строку, которую считали "первой цитатой"
                if kept and kept[-1].strip().startswith(">"):
                    kept.pop()
                break
            continue
        else:
            consecutive_quoted = 0

        kept.append(line)

    # Чистим пустые хвосты
    while kept and not kept[-1].strip():
        kept.pop()
    return "\n".join(kept).strip()


def parse(raw: bytes) -> ParsedEmail:
    """Превращает байты письма в `ParsedEmail`."""
    msg = parse_bytes(raw)

    from_name, from_addr = parseaddr(msg.get("From", ""))
    to_addrs = [a for _, a in getaddresses(msg.get_all("To", []) or []) if a]

    references_hdr = msg.get("References", "") or ""
    references = [r for r in references_hdr.split() if r]

    plain, html_val = _extract_bodies(msg)

    return ParsedEmail(
        message_id=msg.get("Message-ID"),
        in_reply_to=msg.get("In-Reply-To"),
        references=references,
        from_address=(from_addr or "").strip().lower(),
        from_name=from_name or "",
        to_addresses=[a.strip().lower() for a in to_addrs],
        subject=(msg.get("Subject") or "").strip(),
        body_text=plain,
        body_text_clean=clean_reply_text(plain),
        body_html=html_val,
    )
