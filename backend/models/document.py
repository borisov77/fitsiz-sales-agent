"""Модель Document — PDF/вложение, которое агент может отправить лиду."""
from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class DocumentType(str, enum.Enum):
    pricelist = "pricelist"
    catalog = "catalog"
    leaflet = "leaflet"
    commercial_offer = "commercial_offer"
    certificate = "certificate"
    other = "other"


def _uuid() -> str:
    return str(uuid.uuid4())


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255))
    file_path: Mapped[str] = mapped_column(String(500))
    doc_type: Mapped[DocumentType] = mapped_column(
        Enum(DocumentType), default=DocumentType.other, index=True
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, index=True
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Document {self.name} ({self.doc_type})>"
