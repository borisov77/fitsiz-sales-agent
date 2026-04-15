"""CRUD-эндпоинты для лидов + импорт CSV/XLSX."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.lead import Lead, LeadStatus
from backend.schemas import ImportResult, LeadCreate, LeadRead, LeadUpdate
from backend.services.lead_importer import (
    UnsupportedFileFormat,
    import_leads_from_bytes,
)

router = APIRouter(prefix="/api/leads", tags=["leads"])


def _get_or_404(db: Session, lead_id: str) -> Lead:
    lead = db.get(Lead, lead_id)
    if lead is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Lead not found")
    return lead


# ==========================
# Import (перед /{lead_id}, чтобы /import не матчился как id)
# ==========================
@router.post("/import", response_model=ImportResult)
def import_leads(
    db: Annotated[Session, Depends(get_db)],
    file: Annotated[UploadFile, File(...)],
    campaign_id: str | None = Query(default=None),
) -> ImportResult:
    """Импорт лидов из CSV или XLSX.

    Ожидаемые колонки:
    company_name, contact_name, email, phone, city, region,
    company_type, specialization, website, source, notes
    """
    raw = file.file.read()
    try:
        return import_leads_from_bytes(
            db, raw, file.filename or "", campaign_id=campaign_id
        )
    except UnsupportedFileFormat as exc:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=str(exc)
        ) from exc
    except Exception as exc:  # pragma: no cover
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail=f"Failed to parse file: {exc}"
        ) from exc


# ==========================
# CRUD
# ==========================
@router.get("", response_model=list[LeadRead])
def list_leads(
    db: Annotated[Session, Depends(get_db)],
    status_filter: Annotated[LeadStatus | None, Query(alias="status")] = None,
    city: str | None = None,
    campaign_id: str | None = None,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
) -> list[Lead]:
    stmt = select(Lead)
    if status_filter is not None:
        stmt = stmt.where(Lead.status == status_filter)
    if city:
        stmt = stmt.where(Lead.city == city)
    if campaign_id:
        stmt = stmt.where(Lead.campaign_id == campaign_id)
    stmt = stmt.order_by(Lead.created_at.desc()).offset(offset).limit(limit)
    return list(db.execute(stmt).scalars().all())


@router.post("", response_model=LeadRead, status_code=status.HTTP_201_CREATED)
def create_lead(
    payload: LeadCreate, db: Annotated[Session, Depends(get_db)]
) -> Lead:
    existing = db.execute(
        select(Lead).where(Lead.email == payload.email)
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail=f"Lead with email {payload.email} already exists",
        )
    lead = Lead(**payload.model_dump())
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead


@router.get("/{lead_id}", response_model=LeadRead)
def get_lead(lead_id: str, db: Annotated[Session, Depends(get_db)]) -> Lead:
    return _get_or_404(db, lead_id)


@router.patch("/{lead_id}", response_model=LeadRead)
def update_lead(
    lead_id: str,
    payload: LeadUpdate,
    db: Annotated[Session, Depends(get_db)],
) -> Lead:
    lead = _get_or_404(db, lead_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(lead, field, value)
    db.commit()
    db.refresh(lead)
    return lead


@router.delete("/{lead_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lead(lead_id: str, db: Annotated[Session, Depends(get_db)]) -> None:
    lead = _get_or_404(db, lead_id)
    db.delete(lead)
    db.commit()


@router.post("/{lead_id}/transfer", response_model=LeadRead)
def transfer_lead(
    lead_id: str,
    db: Annotated[Session, Depends(get_db)],
    manager: Annotated[str, Query(min_length=1)] = "manager",
) -> Lead:
    """Передаёт лида менеджеру: статус → transferred, assigned_to → <manager>."""
    lead = _get_or_404(db, lead_id)
    lead.status = LeadStatus.transferred
    lead.assigned_to = manager
    lead.next_action_at = None
    db.commit()
    db.refresh(lead)
    return lead
