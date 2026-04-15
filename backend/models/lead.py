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
    new = "new"                    # загружен, ещё не контактировали
    contacted = "contacted"        # отправлено первое письмо
    follow_up_1 = "follow_up_1"    # первый follow-up
    follow_up_2 = "follow_up_2"    # второй follow-up
    follow_up_3 = "follow_up_3"    # финальный follow-up
    replied = "replied"            # ответил (любой ответ)
    interested = "interested"      # проявил интерес
    negotiating = "negotiating"    # обсуждает условия
    warm = "warm"                  # готов к работе
    transferred = "transferred"    # передан менеджеру
    rejected = "rejected"          # отказ
    unsubscribed = "unsubscribed"  # попросил не писать


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
    website: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # --- Состояние ---
    status: Mapped[LeadStatus] = mapped_column(
        Enum(LeadStatus), default=LeadStatus.new, index=True
    )
    campaign_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("campaigns.id", ondelete="SET NULL"), nullable=True
    )
    assigned_to: Mapped[str] = mapped_column(String(100), default="agent")

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
