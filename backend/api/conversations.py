"""Переписки + AI-черновики + режим модерации (approve/edit/send)."""
from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.lead import ColdStage, Lead, LeadStatus
from backend.models.message import Message, MessageDirection, MessageStatus
from backend.services import ai_engine, antispam
from backend.services.cold_template import COLD_TEMPLATE_MARKER
from backend.services.email_sender import EmailSendError, send_email

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


# ==========================
# Схемы
# ==========================
class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    lead_id: str
    direction: MessageDirection
    status: MessageStatus
    subject: str | None
    body_text: str
    attachments: list[str] | None = None
    email_message_id: str | None = None
    in_reply_to: str | None = None
    ai_prompt_used: str | None = None
    created_at: datetime
    sent_at: datetime | None = None


class ConversationRead(BaseModel):
    lead_id: str
    lead_company: str
    lead_email: str
    lead_status: LeadStatus
    messages: list[MessageRead]


class ConversationSummary(BaseModel):
    lead_id: str
    lead_company: str
    lead_email: str
    lead_status: LeadStatus
    last_message_at: datetime | None
    last_message_direction: MessageDirection | None
    total_messages: int
    has_draft: bool


class DraftEdit(BaseModel):
    subject: str | None = None
    body_text: str | None = None
    attachments: list[str] | None = None


class QualifierRead(BaseModel):
    interest_score: int
    buying_readiness: int
    estimated_volume: str
    next_action: str
    transfer_to_manager: bool
    reasoning: str


# ==========================
# Helpers
# ==========================
def _get_lead(db: Session, lead_id: str) -> Lead:
    lead = db.get(Lead, lead_id)
    if lead is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Lead not found")
    return lead


def _get_message(db: Session, message_id: str) -> Message:
    msg = db.get(Message, message_id)
    if msg is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Message not found")
    return msg


def _conversation_messages(db: Session, lead_id: str) -> list[Message]:
    return list(
        db.execute(
            select(Message)
            .where(Message.lead_id == lead_id)
            .order_by(Message.created_at)
        )
        .scalars()
        .all()
    )


def _persist_draft(
    db: Session,
    lead: Lead,
    *,
    subject: str,
    body_text: str,
    attachments: list[str] | None,
    ai_prompt_used: str,
    in_reply_to: str | None = None,
) -> Message:
    msg = Message(
        lead_id=lead.id,
        direction=MessageDirection.outgoing,
        subject=subject,
        body_text=body_text,
        attachments=attachments or None,
        in_reply_to=in_reply_to,
        status=MessageStatus.draft,
        ai_prompt_used=ai_prompt_used,
        created_at=datetime.utcnow(),
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg


def _last_thread_anchor(messages: list[Message]) -> tuple[str | None, list[str]]:
    """Возвращает (in_reply_to, references) для продолжения цепочки.

    Для reply берём Message-ID последнего входящего;
    если входящих нет — Message-ID последнего отправленного нами письма.
    """
    last_incoming = next(
        (m for m in reversed(messages) if m.direction == MessageDirection.incoming),
        None,
    )
    anchor = last_incoming.email_message_id if last_incoming else None
    if anchor is None:
        last_outgoing = next(
            (
                m
                for m in reversed(messages)
                if m.direction == MessageDirection.outgoing
                and m.status == MessageStatus.sent
                and m.email_message_id
            ),
            None,
        )
        anchor = last_outgoing.email_message_id if last_outgoing else None
    # References — собираем все Message-ID по хронологии
    refs = [m.email_message_id for m in messages if m.email_message_id]
    return anchor, refs


# ==========================
# Чтение переписок
# ==========================
@router.get("", response_model=list[ConversationSummary])
def list_conversations(
    db: Annotated[Session, Depends(get_db)],
    status_filter: Annotated[LeadStatus | None, Query(alias="status")] = None,
    limit: int = Query(default=50, ge=1, le=500),
) -> list[ConversationSummary]:
    stmt = select(Lead)
    if status_filter is not None:
        stmt = stmt.where(Lead.status == status_filter)
    leads = list(db.execute(stmt.order_by(Lead.updated_at.desc()).limit(limit)).scalars())

    out: list[ConversationSummary] = []
    for lead in leads:
        messages = _conversation_messages(db, lead.id)
        last = messages[-1] if messages else None
        has_draft = any(m.status == MessageStatus.draft for m in messages)
        out.append(
            ConversationSummary(
                lead_id=lead.id,
                lead_company=lead.company_name,
                lead_email=lead.email,
                lead_status=lead.status,
                last_message_at=(last.sent_at or last.created_at) if last else None,
                last_message_direction=last.direction if last else None,
                total_messages=len(messages),
                has_draft=has_draft,
            )
        )
    return out


@router.get("/{lead_id}", response_model=ConversationRead)
def get_conversation(
    lead_id: str, db: Annotated[Session, Depends(get_db)]
) -> ConversationRead:
    lead = _get_lead(db, lead_id)
    messages = _conversation_messages(db, lead_id)
    return ConversationRead(
        lead_id=lead.id,
        lead_company=lead.company_name,
        lead_email=lead.email,
        lead_status=lead.status,
        messages=[MessageRead.model_validate(m) for m in messages],
    )


# ==========================
# Генерация черновиков
# ==========================
@router.post("/{lead_id}/draft-cold", response_model=MessageRead, status_code=201)
def draft_cold(
    lead_id: str, db: Annotated[Session, Depends(get_db)]
) -> MessageRead:
    """Первое письмо из шаблона (Settings), без AI. Подстановка переменных лида."""
    from backend.services.cold_template import (
        COLD_TEMPLATE_MARKER,
        ColdTemplateError,
        build_first_email,
    )

    lead = _get_lead(db, lead_id)
    try:
        subject, body, attachments = build_first_email(db, lead)
    except ColdTemplateError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    msg = _persist_draft(
        db,
        lead,
        subject=subject,
        body_text=body,
        attachments=attachments,
        ai_prompt_used=COLD_TEMPLATE_MARKER,
    )
    return MessageRead.model_validate(msg)


@router.post("/{lead_id}/draft-reply", response_model=MessageRead, status_code=201)
def draft_reply(
    lead_id: str,
    db: Annotated[Session, Depends(get_db)],
    incoming_message_id: Annotated[str | None, Query()] = None,
) -> MessageRead:
    lead = _get_lead(db, lead_id)
    messages = _conversation_messages(db, lead_id)

    if incoming_message_id:
        incoming = _get_message(db, incoming_message_id)
        if incoming.lead_id != lead_id:
            raise HTTPException(400, detail="Message не принадлежит этому лиду")
    else:
        incoming = next(
            (m for m in reversed(messages) if m.direction == MessageDirection.incoming),
            None,
        )
        if incoming is None:
            raise HTTPException(400, detail="У лида нет входящих сообщений")

    try:
        draft = ai_engine.handle_reply(lead, messages, incoming)
    except ai_engine.AIEngineError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    # Если AI просит не отвечать (автоответ) — не создаём черновик, только двигаем статус
    if not draft.should_send:
        if draft.new_status and draft.new_status != lead.status.value:
            try:
                lead.status = LeadStatus(draft.new_status)
                db.commit()
            except ValueError:
                pass
        raise HTTPException(
            status.HTTP_200_OK,
            detail=f"AI рекомендует не отвечать (intent={draft.intent}). Черновик не создан.",
        )

    # Двигаем статус лида
    if draft.new_status:
        try:
            new_status = LeadStatus(draft.new_status)
            lead.status = new_status
        except ValueError:
            pass

    anchor = incoming.email_message_id
    msg = _persist_draft(
        db,
        lead,
        subject=draft.subject,
        body_text=draft.body_text,
        attachments=draft.attachments,
        ai_prompt_used=f"reply_handler:intent={draft.intent}",
        in_reply_to=anchor,
    )

    # Лид готов к сделке → передача менеджеру (авто или вручную, по настройке)
    if lead.status == LeadStatus.handed_to_manager:
        lead.cold_stage = None
        lead.next_action_at = None  # вне холодной автоматики
        db.commit()
        from backend.services.app_settings import get_auto_transfer

        if get_auto_transfer(db):
            from backend.services.manager_notifier import (
                NotifierError,
                send_manager_report,
            )

            try:
                send_manager_report(db, lead)  # dedup 24ч, бриф + переписка
            except NotifierError:
                # Не валим ответ агента, если SMTP/настройки подвели — лид
                # остаётся handed_to_manager, можно отправить вручную из дашборда.
                pass

    return MessageRead.model_validate(msg)


@router.post("/{lead_id}/draft-followup", response_model=MessageRead, status_code=201)
def draft_followup(
    lead_id: str,
    db: Annotated[Session, Depends(get_db)],
) -> MessageRead:
    """Ручное AI-напоминание в диалоге (одно, без стадий)."""
    lead = _get_lead(db, lead_id)
    messages = _conversation_messages(db, lead_id)

    try:
        draft = ai_engine.generate_follow_up(lead, messages)
    except ai_engine.AIEngineError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    anchor, _refs = _last_thread_anchor(messages)
    msg = _persist_draft(
        db,
        lead,
        subject=draft.subject,
        body_text=draft.body_text,
        attachments=draft.attachments,
        ai_prompt_used=draft.ai_prompt_used,
        in_reply_to=anchor,
    )
    return MessageRead.model_validate(msg)


@router.post("/{lead_id}/qualify", response_model=QualifierRead)
def qualify(lead_id: str, db: Annotated[Session, Depends(get_db)]) -> QualifierRead:
    lead = _get_lead(db, lead_id)
    messages = _conversation_messages(db, lead_id)
    try:
        result = ai_engine.qualify_lead(lead, messages)
    except ai_engine.AIEngineError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return QualifierRead(
        interest_score=result.interest_score,
        buying_readiness=result.buying_readiness,
        estimated_volume=result.estimated_volume,
        next_action=result.next_action,
        transfer_to_manager=result.transfer_to_manager,
        reasoning=result.reasoning,
    )


# ==========================
# Модерация черновиков
# ==========================
@router.patch("/messages/{message_id}", response_model=MessageRead)
def edit_draft(
    message_id: str,
    payload: DraftEdit,
    db: Annotated[Session, Depends(get_db)],
) -> MessageRead:
    msg = _get_message(db, message_id)
    if msg.status != MessageStatus.draft:
        raise HTTPException(400, detail="Редактировать можно только draft")
    if payload.subject is not None:
        msg.subject = payload.subject
    if payload.body_text is not None:
        msg.body_text = payload.body_text
    if payload.attachments is not None:
        msg.attachments = payload.attachments or None
    db.commit()
    db.refresh(msg)
    return MessageRead.model_validate(msg)


@router.delete("/messages/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_draft(message_id: str, db: Annotated[Session, Depends(get_db)]):
    msg = _get_message(db, message_id)
    if msg.status not in (MessageStatus.draft, MessageStatus.queued):
        raise HTTPException(400, detail="Удалять можно только draft или queued")
    db.delete(msg)
    db.commit()
    return None


@router.post("/messages/{message_id}/approve", response_model=MessageRead)
def approve_draft(
    message_id: str, db: Annotated[Session, Depends(get_db)]
) -> MessageRead:
    """Одобряет draft → queued. Отправка запустится scheduler'ом (этап 5)
    или вручную через /send."""
    msg = _get_message(db, message_id)
    if msg.status != MessageStatus.draft:
        raise HTTPException(400, detail="Approve применим только к draft")
    msg.status = MessageStatus.queued
    db.commit()
    db.refresh(msg)
    return MessageRead.model_validate(msg)


@router.post("/messages/{message_id}/send", response_model=MessageRead)
def send_now(
    message_id: str,
    db: Annotated[Session, Depends(get_db)],
) -> MessageRead:
    """Немедленная отправка draft/queued через SMTP (ручная модерация)."""
    msg = _get_message(db, message_id)
    if msg.status not in (MessageStatus.draft, MessageStatus.queued):
        raise HTTPException(400, detail="Отправить можно только draft или queued")

    # Лимит — только для outgoing cold-писем
    if not antispam.under_daily_limit(db):
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Дневной лимит отправки исчерпан",
        )

    lead = _get_lead(db, msg.lead_id)
    messages = _conversation_messages(db, lead.id)
    anchor = msg.in_reply_to
    refs = [
        m.email_message_id
        for m in messages
        if m.email_message_id and m.id != msg.id
    ]

    try:
        result = send_email(
            to=lead.email,
            subject=msg.subject or "FITSIZ",
            body_text=msg.body_text or "",
            attachments=msg.attachments,
            in_reply_to=anchor,
            references=refs or None,
            append_signature=msg.ai_prompt_used
            not in ("cold_template", "cold_reminder"),
        )
    except EmailSendError as exc:
        msg.status = MessageStatus.failed
        db.commit()
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    msg.email_message_id = result.message_id
    msg.status = MessageStatus.sent
    msg.sent_at = result.sent_at

    # Обновляем лида
    lead.last_contact_at = result.sent_at
    if lead.status == LeadStatus.created:
        lead.status = LeadStatus.sent
    # Ручная отправка cold-письма тоже запускает холодный автомат
    if msg.ai_prompt_used == COLD_TEMPLATE_MARKER and lead.status == LeadStatus.sent:
        from datetime import timedelta

        from backend.services.app_settings import get_reminder_delay_days

        lead.cold_stage = ColdStage.awaiting_reply
        lead.next_action_at = result.sent_at + timedelta(
            days=get_reminder_delay_days(db)
        )

    db.commit()
    db.refresh(msg)
    return MessageRead.model_validate(msg)


# ==========================
# Transfer (дубль из leads, но по lead_id из переписки — удобно из UI)
# ==========================
@router.post("/{lead_id}/transfer")
def transfer(
    lead_id: str,
    db: Annotated[Session, Depends(get_db)],
    payload: Annotated[dict[str, Any], Body(default_factory=dict)],
) -> dict[str, object]:
    """Единая точка передачи менеджеру: статус → handed_to_manager + бриф-репорт.

    Ручной клик → force=True (дедуп не глушит). Если адресов менеджеров нет или
    SMTP подвёл — статус всё равно переводится, отправку можно повторить.
    """
    from backend.services.manager_notifier import NotifierError, hand_off_to_manager

    lead = _get_lead(db, lead_id)
    manager = str(payload.get("manager") or "manager")
    report_id: str | None = None
    error: str | None = None
    try:
        report_id = hand_off_to_manager(db, lead, manager=manager, force=True)
    except NotifierError as exc:
        error = str(exc)
    return {
        "lead_id": lead.id,
        "status": lead.status.value,
        "assigned_to": lead.assigned_to,
        "report_message_id": report_id,
        "report_sent": report_id is not None,
        "error": error,
    }
