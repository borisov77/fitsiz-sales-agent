"""Модель Campaign — группа лидов с общим шаблоном и целями."""
from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, Enum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base

if TYPE_CHECKING:
    from backend.models.lead import Lead


class CampaignStatus(str, enum.Enum):
    draft = "draft"
    active = "active"
    paused = "paused"
    completed = "completed"


def _uuid() -> str:
    return str(uuid.uuid4())


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # "cold_retail", "cold_distributor" и т.д.
    template_type: Mapped[str] = mapped_column(String(50), default="cold_retail")

    # Список SKU из каталога, которые продвигаются в кампании
    target_products: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)

    status: Mapped[CampaignStatus] = mapped_column(
        Enum(CampaignStatus), default=CampaignStatus.draft, index=True
    )
    daily_limit: Mapped[int] = mapped_column(Integer, default=20)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    leads: Mapped[list["Lead"]] = relationship("Lead", back_populates="campaign")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Campaign {self.name} [{self.status}]>"
