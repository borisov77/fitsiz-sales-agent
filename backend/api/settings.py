"""Рантайм-настройки через UI: почты менеджеров и режим авто-передачи."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.services import app_settings

router = APIRouter(prefix="/api/settings", tags=["settings"])


class SettingsRead(BaseModel):
    manager_emails: list[str]
    max_manager_emails: int
    auto_transfer_to_manager: bool
    auto_send: bool


class ManagerEmailsUpdate(BaseModel):
    emails: list[str] = Field(default_factory=list)


class AutoTransferUpdate(BaseModel):
    enabled: bool


class AutoSendUpdate(BaseModel):
    enabled: bool


def _read(db: Session) -> SettingsRead:
    return SettingsRead(
        manager_emails=app_settings.get_manager_emails(db),
        max_manager_emails=app_settings.MAX_MANAGER_EMAILS,
        auto_transfer_to_manager=app_settings.get_auto_transfer(db),
        auto_send=app_settings.get_auto_send(db),
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
