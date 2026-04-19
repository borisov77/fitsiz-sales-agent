"""SQLAlchemy-модели FITSIZ Sales Agent."""
from backend.models.app_setting import AppSetting
from backend.models.campaign import Campaign, CampaignStatus
from backend.models.document import Document, DocumentType
from backend.models.lead import CompanyType, Lead, LeadStatus
from backend.models.message import Message, MessageDirection, MessageStatus

__all__ = [
    "Lead",
    "LeadStatus",
    "CompanyType",
    "Message",
    "MessageDirection",
    "MessageStatus",
    "Campaign",
    "CampaignStatus",
    "Document",
    "DocumentType",
    "AppSetting",
]
