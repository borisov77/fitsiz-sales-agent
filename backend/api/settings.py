"""Рантайм-настройки через UI: почты менеджеров и режим авто-передачи."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.services import app_settings
from backend.services import cold_template

router = APIRouter(prefix="/api/settings", tags=["settings"])


class SettingsRead(BaseModel):
    manager_emails: list[str]
    max_manager_emails: int
    auto_transfer_to_manager: bool
    auto_send: bool
    # Сроки холодной зоны
    reminder_delay_days: int
    no_reply_days: int
    # AI-токен: только безопасная сводка, без plaintext
    ai_token_set: bool
    ai_token_masked: str | None = None
    ai_token_source: str | None = None       # 'db' | 'env' | None
    ai_token_can_store_in_db: bool = False    # задан ли FITSIZ_SECRET_KEY


class ManagerEmailsUpdate(BaseModel):
    emails: list[str] = Field(default_factory=list)


class AutoTransferUpdate(BaseModel):
    enabled: bool


class AutoSendUpdate(BaseModel):
    enabled: bool


class ColdTimingUpdate(BaseModel):
    reminder_delay_days: int
    no_reply_days: int


class AiTokenUpdate(BaseModel):
    token: str = ""  # пустая строка → очистить (fallback на .env)


def _read(db: Session) -> SettingsRead:
    tok = app_settings.ai_token_status(db)
    return SettingsRead(
        manager_emails=app_settings.get_manager_emails(db),
        max_manager_emails=app_settings.MAX_MANAGER_EMAILS,
        auto_transfer_to_manager=app_settings.get_auto_transfer(db),
        auto_send=app_settings.get_auto_send(db),
        reminder_delay_days=app_settings.get_reminder_delay_days(db),
        no_reply_days=app_settings.get_no_reply_days(db),
        ai_token_set=bool(tok["is_set"]),
        ai_token_masked=tok["masked"],
        ai_token_source=tok["source"],
        ai_token_can_store_in_db=bool(tok["can_store_in_db"]),
    )


@router.get("", response_model=SettingsRead)
def get_settings(db: Annotated[Session, Depends(get_db)]) -> SettingsRead:
    return _read(db)


@router.put("/manager-emails", response_model=SettingsRead)
def update_manager_emails(
    payload: ManagerEmailsUpdate, db: Annotated[Session, Depends(get_db)]
) -> SettingsRead:
    try:
        app_settings.set_manager_emails(db, payload.emails)
    except app_settings.ManagerEmailsError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _read(db)


@router.patch("/auto-transfer", response_model=SettingsRead)
def update_auto_transfer(
    payload: AutoTransferUpdate, db: Annotated[Session, Depends(get_db)]
) -> SettingsRead:
    app_settings.set_auto_transfer(db, payload.enabled)
    return _read(db)


@router.patch("/auto-send", response_model=SettingsRead)
def update_auto_send(
    payload: AutoSendUpdate, db: Annotated[Session, Depends(get_db)]
) -> SettingsRead:
    app_settings.set_auto_send(db, payload.enabled)
    return _read(db)


@router.put("/cold-timing", response_model=SettingsRead)
def update_cold_timing(
    payload: ColdTimingUpdate, db: Annotated[Session, Depends(get_db)]
) -> SettingsRead:
    try:
        app_settings.set_cold_timing(
            db, payload.reminder_delay_days, payload.no_reply_days
        )
    except app_settings.ColdTimingError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _read(db)


@router.put("/ai-token", response_model=SettingsRead)
def update_ai_token(
    payload: AiTokenUpdate, db: Annotated[Session, Depends(get_db)]
) -> SettingsRead:
    """Сохраняет AI-токен (шифрованно) или очищает (пустая строка → fallback .env).
    Ответ — только маска, plaintext никогда не возвращается."""
    from backend.services import crypto

    try:
        app_settings.set_ai_token(db, payload.token)
    except crypto.CryptoError as exc:
        # Текст исключения не содержит секретов (см. crypto.py)
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _read(db)


# ==========================
# Шаблон первого письма
# ==========================
class ColdTemplate(BaseModel):
    subject: str
    body: str
    signature: str


@router.get("/cold-template", response_model=ColdTemplate)
def get_cold_template(db: Annotated[Session, Depends(get_db)]) -> ColdTemplate:
    return ColdTemplate(**cold_template.get_template(db))


@router.put("/cold-template", response_model=ColdTemplate)
def update_cold_template(
    payload: ColdTemplate, db: Annotated[Session, Depends(get_db)]
) -> ColdTemplate:
    tpl = cold_template.set_template(
        db, payload.subject, payload.body, payload.signature
    )
    return ColdTemplate(**tpl)
