"""Статус кампании для дашборда: очередь, отправлено, ожидания, тёплые."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.lead import Lead, LeadStatus
from backend.models.message import Message, MessageDirection, MessageStatus
from backend.services import antispam

router = APIRouter(prefix="/api/campaign", tags=["campaign"])


class CampaignStatus(BaseModel):
    queued: int            # писем в очереди на отправку
    sent_today: int        # отправлено сегодня
    awaiting_reply: int    # написали, ждём ответа
    replied: int           # ответили (в работе)
    warm: int              # тёплые


_AWAITING = (
    LeadStatus.contacted,
    LeadStatus.follow_up_1,
    LeadStatus.follow_up_2,
    LeadStatus.follow_up_3,
)
_REPLIED = (LeadStatus.replied, LeadStatus.interested, LeadStatus.negotiating)


def _count_leads(db: Session, statuses) -> int:
    return int(
        db.execute(
            select(func.count(Lead.id)).where(Lead.status.in_(statuses))
        ).scalar_one()
        or 0
    )


@router.get("/status", response_model=CampaignStatus)
def campaign_status(db: Annotated[Session, Depends(get_db)]) -> CampaignStatus:
    queued = int(
        db.execute(
            select(func.count(Message.id)).where(
                Message.direction == MessageDirection.outgoing,
                Message.status == MessageStatus.queued,
            )
        ).scalar_one()
        or 0
    )
    return CampaignStatus(
        queued=queued,
        sent_today=antispam.count_outgoing_sent_today(db),
        awaiting_reply=_count_leads(db, _AWAITING),
        replied=_count_leads(db, _REPLIED),
        warm=_count_leads(db, (LeadStatus.warm,)),
    )
