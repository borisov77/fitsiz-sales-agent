"""Модель Message — отдельное письмо (входящее или исходящее)."""
from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base

if TYPE_CHECKING:
    from backend.models.lead import Lead


class MessageDirection(str, enum.Enum):
    outgoing = "outgoing"
    incoming = "incoming"


class MessageStatus(str, enum.Enum):
    draft = "draft"            # AI сгенерировал, ожидает одобрения / отправки
    queued = "queued"          # в очереди на отправку
    sent = "sent"              # отправлено через SMTP
    delivered = "delivered"    # подтверждена доставка (если есть DSN)
    read = "read"              # прочитано (если доступно)
    bounced = "bounced"        # bounce
    received = "received"      # входящее, успешно распарсено
    failed = "failed"          # ошибка отправки


def _uuid() -> str:
    return str(uuid.uuid4())


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)

    lead_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("leads.id", ondelete="CASCADE"), index=True
    )

    direction: Mapped[MessageDirection] = mapped_column(Enum(MessageDirection))
    subject: Mapped[str | None] = mapped_column(String(500), nullable=True)
    body_text: Mapped[str] = mapped_column(Text, default="")
    body_html: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Список имён файлов из каталога documents/
    attachments: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)

    # Email-заголовки для threading
    email_message_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True
    )
    in_reply_to: Mapped[str | None] = mapped_column(String(255), nullable=True)

    status: Mapped[MessageStatus] = mapped_column(
        Enum(MessageStatus), default=MessageStatus.draft, index=True
    )

    # Для отладки: какой промпт породил это сообщение
    ai_prompt_used: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, index=True
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    lead: Mapped["Lead"] = relationship("Lead", back_populates="messages")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Message {self.direction} lead={self.lead_id} [{self.status}]>"
