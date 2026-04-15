"""CRUD-эндпоинты для лидов + импорт CSV/XLSX."""
from __future__ import annotations

import csv
import io
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.lead import CompanyType, Lead, LeadStatus
from backend.schemas import ImportResult, LeadCreate, LeadRead, LeadUpdate

router = APIRouter(prefix="/api/leads", tags=["leads"])


# ==========================
# Helpers
# ==========================
def _get_or_404(db: Session, lead_id: str) -> Lead:
    lead = db.get(Lead, lead_id)
    if lead is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Lead not found")
    return lead


def _parse_company_type(value: str | None) -> CompanyType:
    if not value:
        return CompanyType.other
    value = value.strip().lower()
    try:
        return CompanyType(value)
    except ValueError:
        return CompanyType.other


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
    # Дубли по email не допускаем
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


# ==========================
# Import CSV/XLSX
# ==========================
EXPECTED_COLUMNS = {
    "company_name",
    "contact_name",
    "email",
    "phone",
    "city",
    "region",
    "company_type",
    "specialization",
    "website",
    "source",
    "notes",
}


def _normalize_row(row: dict[str, str | None]) -> dict[str, object]:
    """Очищаем значения + приводим пустые к None."""
    cleaned: dict[str, object] = {}
    for key, value in row.items():
        if key is None:
            continue
        k = key.strip()
        if isinstance(value, str):
            value = value.strip()
            value = value or None
        cleaned[k] = value
    return cleaned


def _parse_csv(raw: bytes) -> list[dict[str, object]]:
    text = raw.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    return [_normalize_row(row) for row in reader]


def _parse_xlsx(raw: bytes) -> list[dict[str, object]]:
    # Ленивый импорт — pandas/openpyxl тяжёлые
    import pandas as pd

    df = pd.read_excel(io.BytesIO(raw), dtype=str).fillna("")
    df.columns = [str(c).strip() for c in df.columns]
    rows = df.to_dict(orient="records")
    return [_normalize_row({k: v for k, v in r.items()}) for r in rows]


@router.post("/import", response_model=ImportResult)
def import_leads(
    db: Annotated[Session, Depends(get_db)],
    file: Annotated[UploadFile, File(...)],
    campaign_id: str | None = Query(default=None),
) -> ImportResult:
    """Импорт лидов из CSV или XLSX.

    Ожидаемые колонки:
    company_name, contact_name, email, city, region,
    company_type, specialization, website, source, notes
    """
    filename = (file.filename or "").lower()
    raw = file.file.read()

    try:
        if filename.endswith(".csv"):
            rows = _parse_csv(raw)
        elif filename.endswith((".xlsx", ".xls")):
            rows = _parse_xlsx(raw)
        else:
            raise HTTPException(
                status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="Expected .csv or .xlsx file",
            )
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail=f"Failed to parse file: {exc}"
        ) from exc

    total = len(rows)
    created_ids: list[str] = []
    skipped = 0
    errors: list[str] = []

    # Кэшируем уже существующие email-ы, чтобы не делать N+1 запросов
    existing_emails = {
        e for (e,) in db.execute(select(Lead.email)).all() if e is not None
    }

    for idx, row in enumerate(rows, start=2):  # 2 = учитывая строку-заголовок
        email = (row.get("email") or "").strip().lower() if row.get("email") else None
        company = (row.get("company_name") or "").strip() if row.get("company_name") else None

        if not email or not company:
            errors.append(f"Row {idx}: missing email or company_name")
            continue

        if email in existing_emails:
            skipped += 1
            continue

        try:
            lead = Lead(
                company_name=company,
                contact_name=row.get("contact_name"),
                email=email,
                phone=row.get("phone"),
                city=row.get("city"),
                region=row.get("region"),
                company_type=_parse_company_type(row.get("company_type")),  # type: ignore[arg-type]
                specialization=row.get("specialization"),
                website=row.get("website"),
                source=row.get("source"),
                notes=row.get("notes"),
                campaign_id=campaign_id,
                status=LeadStatus.new,
                created_at=datetime.utcnow(),
            )
            db.add(lead)
            db.flush()
            created_ids.append(lead.id)
            existing_emails.add(email)
        except Exception as exc:  # pragma: no cover
            errors.append(f"Row {idx}: {exc}")

    db.commit()

    return ImportResult(
        total_rows=total,
        created=len(created_ids),
        skipped_duplicates=skipped,
        errors=errors,
        created_ids=created_ids,
    )
