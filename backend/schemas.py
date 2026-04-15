"""Pydantic-схемы для API (вход/выход)."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from backend.models.lead import CompanyType, LeadStatus


# ==========================
# Lead
# ==========================
class LeadBase(BaseModel):
    company_name: str = Field(..., min_length=1, max_length=255)
    contact_name: str | None = Field(default=None, max_length=255)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=50)
    city: str | None = Field(default=None, max_length=100)
    region: str | None = Field(default=None, max_length=100)
    company_type: CompanyType = CompanyType.other
    specialization: str | None = None
    website: str | None = Field(default=None, max_length=255)
    source: str | None = Field(default=None, max_length=100)
    notes: str | None = None


class LeadCreate(LeadBase):
    campaign_id: str | None = None


class LeadUpdate(BaseModel):
    company_name: str | None = None
    contact_name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    city: str | None = None
    region: str | None = None
    company_type: CompanyType | None = None
    specialization: str | None = None
    website: str | None = None
    source: str | None = None
    notes: str | None = None
    status: LeadStatus | None = None
    campaign_id: str | None = None
    assigned_to: str | None = None
    next_action_at: datetime | None = None


class LeadRead(LeadBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: LeadStatus
    campaign_id: str | None
    assigned_to: str
    created_at: datetime
    updated_at: datetime
    last_contact_at: datetime | None
    next_action_at: datetime | None


class ImportResult(BaseModel):
    """Ответ на POST /api/leads/import."""

    total_rows: int
    created: int
    skipped_duplicates: int
    errors: list[str] = Field(default_factory=list)
    created_ids: list[str] = Field(default_factory=list)
