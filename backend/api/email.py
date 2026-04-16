"""Тестовые email-эндпоинты: ручная проверка SMTP/IMAP из dashboard."""
from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.message import Message, MessageDirection, MessageStatus
from backend.services import antispam
from backend.services.email_reader import EmailReadError, FetchSummary, fetch_new_messages
from backend.services.email_sender import (
    EmailSendError,
    SendResult,
    send_email,
)

router = APIRouter(prefix="/api/email", tags=["email"])


class SendTestRequest(BaseModel):
    to: EmailStr
    subject: str = Field(default="Тест FITSIZ Sales Agent")
    body_text: str = Field(default="Тестовое письмо от агента. Если вы это читаете — SMTP настроен.")
    attachments: list[str] | None = None
    lead_id: str | None = None  # если передан — сохраним Message в истории лида


class SendTestResponse(BaseModel):
    message_id: str
    sent_at: datetime
    to: str
    subject: str
    saved_message_id: str | None = None


class QuotaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    sent_today: int
    daily_limit: int
    remaining: int


class FetchInboxResponse(BaseModel):
    checked: int
    matched: int
    unmatched: int
    saved_message_ids: list[str]
    updated_lead_ids: list[str]


# ==========================
# Отправка тестового письма
# ==========================
@router.post("/send-test", response_model=SendTestResponse)
def send_test(
    payload: SendTestRequest,
    db: Annotated[Session, Depends(get_db)],
) -> SendTestResponse:
    try:
        result: SendResult = send_email(
            to=payload.to,
            subject=payload.subject,
            body_text=payload.body_text,
            attachments=payload.attachments,
        )
    except EmailSendError as exc:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY, detail=str(exc)
        ) from exc

    saved_id: str | None = None
    if payload.lead_id:
        msg = Message(
            lead_id=payload.lead_id,
            direction=MessageDirection.outgoing,
            subject=payload.subject,
            body_text=payload.body_text,
            attachments=payload.attachments,
            email_message_id=result.message_id,
            status=MessageStatus.sent,
            sent_at=result.sent_at,
            ai_prompt_used="manual:send-test",
            created_at=datetime.utcnow(),
        )
        db.add(msg)
        db.commit()
        db.refresh(msg)
        saved_id = msg.id

    return SendTestResponse(
        message_id=result.message_id,
        sent_at=result.sent_at,
        to=result.to,
        subject=result.subject,
        saved_message_id=saved_id,
    )


# ==========================
# Квота на сегодня
# ==========================
@router.get("/quota", response_model=QuotaResponse)
def get_quota(db: Annotated[Session, Depends(get_db)]) -> QuotaResponse:
    from backend.config import settings

    sent = antispam.count_outgoing_sent_today(db)
    remaining = antispam.remaining_daily_quota(db)
    return QuotaResponse(
        sent_today=sent,
        daily_limit=settings.max_cold_emails_per_day,
        remaining=remaining,
    )


# ==========================
# Ручной pull входящих
# ==========================
@router.post("/check-inbox", response_model=FetchInboxResponse)
def check_inbox(
    db: Annotated[Session, Depends(get_db)],
    mark_as_seen: bool = True,
    limit: int | None = None,
) -> FetchInboxResponse:
    try:
        summary: FetchSummary = fetch_new_messages(
            db, mark_as_seen=mark_as_seen, limit=limit
        )
    except EmailReadError as exc:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY, detail=str(exc)
        ) from exc

    return FetchInboxResponse(
        checked=summary.checked,
        matched=summary.matched,
        unmatched=summary.unmatched,
        saved_message_ids=summary.saved_messages,
        updated_lead_ids=summary.updated_leads,
    )


# ==========================
# Тестовое уведомление менеджеру
# ==========================
@router.post("/test-manager-email")
def test_manager_email(db: Annotated[Session, Depends(get_db)]) -> dict[str, str]:
    """Отправляет тестовый warm-alert на MANAGER_EMAIL с фиктивным лидом."""
    from backend.services.manager_notifier import (
        NotifierError,
        send_test_manager_notification,
    )

    try:
        message_id = send_test_manager_notification(db)
    except NotifierError as exc:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY, detail=str(exc)
        ) from exc
    return {"status": "sent", "message_id": message_id}
