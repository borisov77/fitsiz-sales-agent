"""Модель Lead — потенциальный B2B-клиент FITSIZ."""
from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base

if TYPE_CHECKING:
    from backend.models.campaign import Campaign
    from backend.models.message import Message


class CompanyType(str, enum.Enum):
    retailer = "retailer"
    distributor = "distributor"
    manufacturer = "manufacturer"
    other = "other"


class LeadStatus(str, enum.Enum):
    """Семь бизнес-статусов воронки — единственное, что видит дашборд.

    Под-состояния холодной автоматики НЕ живут здесь — для них служебное
    поле `cold_stage` (см. ниже). Это держит бизнес-словарь чистым под
    White Label: значения переименовываются/перекрашиваются 1:1.
    """

    created = "created"                      # 1. загружен/создан, рассылка не запущена
    sent = "sent"                            # 2. cold ушло, идёт холодный автомат
    in_dialog = "in_dialog"                  # 3. лид ответил, ведётся переписка
    handed_to_manager = "handed_to_manager"  # 4. передан менеджеру с репортом
    won = "won"                              # 5. заключён договор
    lost = "lost"                            # 6. сделка не состоялась (+ close_reason)
    no_reply = "no_reply"                    # 7. осталось без ответа (видимый, не терминал)


class ColdStage(str, enum.Enum):
    """Под-состояние ВНУТРИ статуса `sent` — деталь холодной автоматики.

    Никогда не показывается в UI. Осмысленно только при `status == sent`;
    в остальных статусах = NULL. Инвариант: cold_stage != NULL ⇒ status == sent.
    """

    awaiting_reply = "awaiting_reply"  # cold ушло, напоминание ещё не слали
    reminder_sent = "reminder_sent"    # напоминание ушло, ждём финальный срок → no_reply


def _uuid() -> str:
    return str(uuid.uuid4())


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)

    # --- Компания ---
    company_name: Mapped[str] = mapped_column(String(255), index=True)
    contact_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str] = mapped_column(String(255), index=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    region: Mapped[str | None] = mapped_column(String(100), nullable=True)
    company_type: Mapped[CompanyType] = mapped_column(
        Enum(CompanyType), default=CompanyType.other
    )
    specialization: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Свободное описание компании: чем занимается, что важно знать боту.
    # Передаётся в контекст при генерации cold-письма.
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    website: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # --- Состояние ---
    status: Mapped[LeadStatus] = mapped_column(
        Enum(LeadStatus), default=LeadStatus.created, index=True
    )
    # Под-состояние холодной зоны (только при status==sent), не показывается в UI.
    cold_stage: Mapped[ColdStage | None] = mapped_column(
        Enum(ColdStage), nullable=True
    )
    campaign_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("campaigns.id", ondelete="SET NULL"), nullable=True
    )
    # Информационное поле (кто ведёт). Гейтом автоматики БОЛЬШЕ не является —
    # автозадачи отбирают лидов строго по status.
    assigned_to: Mapped[str] = mapped_column(String(100), default="agent")

    # --- Закрытие сделки (статусы won / lost) ---
    close_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # --- Времена ---
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    last_contact_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    next_action_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, index=True
    )

    # --- Связи ---
    messages: Mapped[list["Message"]] = relationship(
        "Message",
        back_populates="lead",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )
    campaign: Mapped["Campaign | None"] = relationship(
        "Campaign", back_populates="leads"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Lead {self.company_name} [{self.status}]>"
