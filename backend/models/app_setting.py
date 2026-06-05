"""Key-value настройки, которые можно менять в рантайме без рестарта backend'а.

Пример: дневной лимит cold-писем. В .env лежит базовое значение, но можно
переопределить через UI — тогда override хранится здесь.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class AppSetting(Base):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    # TEXT, а не VARCHAR(255): сюда кладётся в т.ч. шифртекст Fernet AI-токена
    # (~200+ символов), который в ограниченную длину не помещается.
    value: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<AppSetting {self.key}={self.value!r}>"
