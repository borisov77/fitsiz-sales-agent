"""CRUD-эндпоинты для лидов + импорт CSV/XLSX."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.lead import Lead, LeadStatus
from backend.schemas import (
    ImportResult,
    LeadCreate,
    LeadRead,
    LeadUpdate,
    ManualLeadCreate,
)
from backend.services.lead_importer import (
    CSV_TEMPLATE,
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
# Ручное добавление + CSV-шаблон (до /{lead_id})
# ==========================
@router.get("/csv-template")
def csv_template() -> Response:
    """Отдаёт образец CSV единого формата: company_name,email,description,contact_name."""
    return Response(
        content=CSV_TEMPLATE,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="leads_template.csv"'
        },
    )


@router.post("/manual", response_model=LeadRead, status_code=status.HTTP_201_CREATED)
def create_lead_manual(
    payload: ManualLeadCreate, db: Annotated[Session, Depends(get_db)]
) -> Lead:
    """Создаёт лида вручную по единому формату. Проверяет дубль по email."""
    email = payload.email.strip().lower()
    existing = db.execute(
        select(Lead).where(Lead.email == email)
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail=f"Лид с таким email уже есть: {email}",
        )
    lead = Lead(
        company_name=payload.company_name.strip(),
        email=email,
        description=payload.description.strip(),
        contact_name=(payload.contact_name or None),
        source="manual",
        status=LeadStatus.new,
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead


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
def delete_lead(lead_id: str, db: Annotated[Session, Depends(get_db)]):
    lead = _get_or_404(db, lead_id)
    db.delete(lead)
    db.commit()
    return None


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


@router.post("/{lead_id}/notify-manager")
def notify_manager(
    lead_id: str, db: Annotated[Session, Depends(get_db)]
) -> dict[str, object]:
    """Ручная отправка уведомления о лиде на все почты менеджеров."""
    from backend.services.app_settings import get_manager_emails
    from backend.services.manager_notifier import (
        NotifierError,
        notify_manager_about_warm_lead,
    )

    lead = _get_or_404(db, lead_id)
    recipients = get_manager_emails(db)
    if not recipients:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Добавьте хотя бы одну почту менеджера в Настройках",
        )

    # Последнее входящее сообщение клиента — в тело уведомления
    last_incoming = next(
        (
            m.body_text
            for m in sorted(lead.messages, key=lambda x: x.created_at, reverse=True)
            if m.direction.value == "incoming"
        ),
        None,
    )
    try:
        message_id = notify_manager_about_warm_lead(
            db, lead, last_incoming_text=last_incoming, force=True
        )
    except NotifierError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    # Помечаем, что лид передан
    if lead.status == LeadStatus.warm:
        lead.status = LeadStatus.transferred
        db.commit()

    return {
        "status": "sent",
        "recipients": recipients,
        "message_id": message_id,
    }
