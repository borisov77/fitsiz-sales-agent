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
    awaiting_reply: int    # холодные, ждём ответа (status=sent)
    in_dialog: int         # ведётся переписка
    handed: int            # передано менеджеру


def _count_status(db: Session, status: LeadStatus) -> int:
    return int(
        db.execute(
            select(func.count(Lead.id)).where(Lead.status == status)
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
        awaiting_reply=_count_status(db, LeadStatus.sent),
        in_dialog=_count_status(db, LeadStatus.in_dialog),
        handed=_count_status(db, LeadStatus.handed_to_manager),
    )


# ==========================
# Конверсионная воронка
# ==========================
class FunnelStep(BaseModel):
    key: str
    reached: int          # «дошёл хотя бы до этого этапа» (кумулятивно, убывает)


class FunnelConversions(BaseModel):
    reply_rate: float       # ответили / отправлено
    qualify_rate: float     # передано менеджеру / ответили
    deal_rate: float        # договор / передано менеджеру
    no_reply_share: float   # доля «осталось без ответа» (от отправленных)
    lost_share: float       # доля «отказ» (от отправленных)


class FunnelRead(BaseModel):
    total: int
    counts: dict[str, int]          # сырые счётчики по 7 статусам
    steps: list[FunnelStep]         # убывающие ступени created→sent→in_dialog→handed→won
    terminals: dict[str, int]       # lost / no_reply (сбоку)
    conversions: FunnelConversions


def _pct(a: int, b: int) -> float:
    return round(100.0 * a / b, 1) if b else 0.0


@router.get("/funnel", response_model=FunnelRead)
def funnel(db: Annotated[Session, Depends(get_db)]) -> FunnelRead:
    """Воронка по 7 статусам: сырые счётчики + кумулятивные ступени + конверсии.

    Ступени считаются по принципу «дошёл хотя бы до этапа», поэтому монотонно
    убывают и ложатся в воронку. Поверх этой структуры позже встанут графики.
    """
    rows = db.execute(
        select(Lead.status, func.count(Lead.id)).group_by(Lead.status)
    ).all()
    counts = {s.value: 0 for s in LeadStatus}
    for st, c in rows:
        counts[st.value if hasattr(st, "value") else str(st)] = int(c)

    total = sum(counts.values())
    created = counts["created"]
    reached_sent = total - created  # все, кому ушло холодное письмо и дальше
    responded = (
        counts["in_dialog"] + counts["handed_to_manager"] + counts["won"] + counts["lost"]
    )
    ever_handed = counts["handed_to_manager"] + counts["won"] + counts["lost"]
    won = counts["won"]

    steps = [
        FunnelStep(key="created", reached=total),
        FunnelStep(key="sent", reached=reached_sent),
        FunnelStep(key="in_dialog", reached=responded),
        FunnelStep(key="handed_to_manager", reached=ever_handed),
        FunnelStep(key="won", reached=won),
    ]
    conversions = FunnelConversions(
        reply_rate=_pct(responded, reached_sent),
        qualify_rate=_pct(ever_handed, responded),
        deal_rate=_pct(won, ever_handed),
        no_reply_share=_pct(counts["no_reply"], reached_sent),
        lost_share=_pct(counts["lost"], reached_sent),
    )
    return FunnelRead(
        total=total,
        counts=counts,
        steps=steps,
        terminals={"lost": counts["lost"], "no_reply": counts["no_reply"]},
        conversions=conversions,
    )
