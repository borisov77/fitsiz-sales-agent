"""AI-мозг агента: обёртка над Anthropic API.

Функции:
  - generate_cold_email(lead)         — первое холодное письмо
  - handle_reply(lead, incoming_msg)  — ответ на входящее
  - generate_follow_up(lead, stage)   — follow-up 1/2/3
  - qualify_lead(lead)                — оценка интереса/готовности/объёма

Ключевые решения:
  - Промпты и база знаний читаются из .md (hot-reload не нужен: они меняются
    редко, кешируются на уровне процесса).
  - System prompt помечен `cache_control: ephemeral` — первый вызов
    прогревает кеш Anthropic (5-минутный TTL), дальше токены считаются
    по cache-read тарифу. На больших объёмах это экономит ~90% input-cost.
  - Структурированный вывод — через обязательное `tool_use`. Модель не
    «кое-как отдаст JSON», а вернёт валидный JSON по схеме инструмента.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

from backend.config import BASE_DIR, settings
from backend.models.lead import Lead
from backend.models.message import Message, MessageDirection


log = logging.getLogger(__name__)

PROMPTS_DIR = BASE_DIR / "backend" / "prompts"
KNOWLEDGE_DIR = BASE_DIR / "backend" / "knowledge"
DOCUMENTS_DIR = BASE_DIR / "documents"

# Типы файлов, которые имеет смысл прикладывать к письму
_ATTACHMENT_EXTENSIONS = {
    ".pdf", ".xlsx", ".xls", ".docx", ".doc", ".jpg", ".jpeg", ".png",
}


def allowed_attachments() -> set[str]:
    """Фактические файлы из `documents/`, которые агент может приложить.

    Сканируется на каждом вызове — только что загруженный файл подхватывается
    без перезапуска. Источник истины — реальная папка, а не статический список:
    если файла нет на диске, агент не сможет его предложить (имя отфильтруется
    в `_filter_attachments`). Скрытые файлы (`.DS_Store`, `.gitkeep`) игнорим.
    """
    if not DOCUMENTS_DIR.is_dir():
        return set()
    return {
        p.name
        for p in DOCUMENTS_DIR.iterdir()
        if p.is_file()
        and not p.name.startswith(".")
        and p.suffix.lower() in _ATTACHMENT_EXTENSIONS
    }


class AIEngineError(RuntimeError):
    """Любая ошибка уровня AI-движка (сеть, парсинг, пустой ответ)."""


# ==========================
# Рендеринг шаблонов
# ==========================
_PLACEHOLDER = re.compile(r"\{(\w+)\}")


def _render(template: str, **vars: Any) -> str:
    """`{known_var}` → значение, неизвестные плейсхолдеры оставляем как есть.

    Это безопаснее `str.format`: JSON-примеры в промптах типа `{ "key": ... }`
    не матчатся (между `{` и `}` нужен только \w — одно слово).
    """
    def repl(m: re.Match[str]) -> str:
        key = m.group(1)
        value = vars.get(key)
        if value is None or value == "":
            return "—"
        return str(value)

    return _PLACEHOLDER.sub(repl, template)


@lru_cache(maxsize=32)
def _load_prompt(name: str) -> str:
    path = PROMPTS_DIR / f"{name}.md"
    if not path.is_file():
        raise AIEngineError(f"Промпт не найден: {path}")
    return path.read_text(encoding="utf-8")


@lru_cache(maxsize=1)
def _load_knowledge() -> dict[str, str]:
    files = {
        "product_catalog": "product_catalog.md",
        "pricing": "pricing.md",
        "competitors": "competitors.md",
        "faq": "faq.md",
        "objections": "objections.md",
    }
    out: dict[str, str] = {}
    for key, filename in files.items():
        path = KNOWLEDGE_DIR / filename
        if not path.is_file():
            raise AIEngineError(f"Файл базы знаний не найден: {path}")
        out[key] = path.read_text(encoding="utf-8")
    return out


def _build_system_prompt() -> str:
    tmpl = _load_prompt("system_prompt")
    knowledge = _load_knowledge()
    return _render(
        tmpl,
        agent_name=settings.agent_name,
        agent_title=settings.agent_title,
        agent_phone=settings.agent_phone,
        agent_signature=settings.agent_signature,
        **knowledge,
    )


# ==========================
# Anthropic client
# ==========================
_client = None


def _get_client():
    """Ленивая инициализация — тесты парсеров/шаблонов не требуют API-ключа."""
    global _client
    if _client is not None:
        return _client
    if not settings.anthropic_api_key:
        raise AIEngineError("ANTHROPIC_API_KEY не задан в .env")
    try:
        from anthropic import Anthropic  # ленивый импорт
    except ImportError as exc:  # pragma: no cover
        raise AIEngineError(
            "Пакет `anthropic` не установлен: pip install anthropic"
        ) from exc
    _client = Anthropic(api_key=settings.anthropic_api_key)
    return _client


# ==========================
# JSON tools (структурированный вывод)
# ==========================
def _tool_cold_email() -> dict[str, Any]:
    return {
        "name": "draft_cold_email",
        "description": "Возврат первого cold-письма для лида",
        "input_schema": {
            "type": "object",
            "properties": {
                "subject": {"type": "string"},
                "body_text": {"type": "string"},
                "reasoning": {"type": "string"},
            },
            "required": ["subject", "body_text"],
        },
    }


def _tool_reply() -> dict[str, Any]:
    return {
        "name": "draft_reply",
        "description": "Классификация входящего и ответное письмо",
        "input_schema": {
            "type": "object",
            "properties": {
                "intent": {
                    "type": "string",
                    "enum": [
                        "interest",
                        "question",
                        "objection",
                        "ready",
                        "reject",
                        "unsubscribe",
                        "autoreply",
                        "out_of_scope",
                    ],
                },
                "new_status": {
                    "type": "string",
                    "enum": [
                        "contacted",
                        "replied",
                        "interested",
                        "negotiating",
                        "warm",
                        "transferred",
                        "rejected",
                        "unsubscribed",
                    ],
                },
                "reply_subject": {"type": "string"},
                "reply_text": {"type": "string"},
                "attachments": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "is_warm": {"type": "boolean"},
                "should_send": {"type": "boolean"},
                "reasoning": {"type": "string"},
            },
            "required": [
                "intent",
                "new_status",
                "reply_text",
                "is_warm",
                "should_send",
            ],
        },
    }


def _tool_follow_up() -> dict[str, Any]:
    return {
        "name": "draft_follow_up",
        "description": "Follow-up письмо",
        "input_schema": {
            "type": "object",
            "properties": {
                "subject": {"type": "string"},
                "body_text": {"type": "string"},
                "attachments": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "reasoning": {"type": "string"},
            },
            "required": ["subject", "body_text"],
        },
    }


def _tool_qualifier() -> dict[str, Any]:
    return {
        "name": "qualify_lead",
        "description": "Оценка лида",
        "input_schema": {
            "type": "object",
            "properties": {
                "interest_score": {"type": "integer", "minimum": 1, "maximum": 10},
                "buying_readiness": {"type": "integer", "minimum": 1, "maximum": 10},
                "estimated_volume": {
                    "type": "string",
                    "enum": ["small", "medium", "large", "strategic", "unknown"],
                },
                "next_action": {"type": "string"},
                "transfer_to_manager": {"type": "boolean"},
                "reasoning": {"type": "string"},
            },
            "required": [
                "interest_score",
                "buying_readiness",
                "estimated_volume",
                "transfer_to_manager",
            ],
        },
    }


# ==========================
# Общая точка вызова API
# ==========================
def _call_with_tool(
    user_message: str,
    tool: dict[str, Any],
    *,
    max_tokens: int = 1500,
    temperature: float = 0.6,
) -> dict[str, Any]:
    """Зовёт Anthropic с forced tool-use. Возвращает распарсенный input."""
    client = _get_client()
    system_prompt = _build_system_prompt()

    try:
        response = client.messages.create(
            model=settings.ai_model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=[
                {
                    "type": "text",
                    "text": system_prompt,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            tools=[tool],
            tool_choice={"type": "tool", "name": tool["name"]},
            messages=[{"role": "user", "content": user_message}],
        )
    except Exception as exc:  # pragma: no cover
        raise AIEngineError(f"Anthropic API ошибка: {exc}") from exc

    # Ищем tool_use-блок в ответе
    for block in response.content:
        if getattr(block, "type", None) == "tool_use":
            raw = getattr(block, "input", None)
            if isinstance(raw, dict):
                return raw
            if isinstance(raw, str):
                try:
                    return json.loads(raw)
                except json.JSONDecodeError as exc:
                    raise AIEngineError(
                        f"Не удалось распарсить tool_use input как JSON: {raw[:200]}"
                    ) from exc

    raise AIEngineError(
        f"В ответе нет tool_use-блока: {response.content!r}"
    )


# ==========================
# Результаты
# ==========================
@dataclass
class DraftEmail:
    subject: str
    body_text: str
    attachments: list[str] = field(default_factory=list)
    reasoning: str = ""
    ai_prompt_used: str = ""
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class ReplyDraft(DraftEmail):
    intent: str = ""
    new_status: str = ""
    is_warm: bool = False
    should_send: bool = True


@dataclass
class QualifierResult:
    interest_score: int
    buying_readiness: int
    estimated_volume: str
    next_action: str
    transfer_to_manager: bool
    reasoning: str = ""
    raw: dict[str, Any] = field(default_factory=dict)


# ==========================
# Утилиты
# ==========================
def _format_history(messages: list[Message]) -> str:
    """Человекочитаемая история переписки для промпта."""
    if not messages:
        return "(переписки ещё не было)"
    parts: list[str] = []
    for m in messages:
        who = "FITSIZ" if m.direction == MessageDirection.outgoing else "Клиент"
        when = (m.sent_at or m.created_at or datetime.utcnow()).strftime("%Y-%m-%d %H:%M")
        subject = m.subject or "(без темы)"
        body = (m.body_text or "").strip() or "(пусто)"
        parts.append(f"--- {who}, {when} — {subject} ---\n{body}")
    return "\n\n".join(parts)


def _filter_attachments(names: list[str] | None) -> list[str]:
    if not names:
        return []
    allowed = allowed_attachments()
    return [n for n in names if n in allowed]


def _sent_documents(messages: list[Message]) -> list[str]:
    seen: list[str] = []
    for m in messages:
        if m.direction != MessageDirection.outgoing:
            continue
        for att in m.attachments or []:
            if att not in seen:
                seen.append(att)
    return seen


# ==========================
# Публичный API
# ==========================
def generate_cold_email(lead: Lead) -> DraftEmail:
    """Генерирует первое холодное письмо для лида."""
    user_prompt = _render(
        _load_prompt("cold_email"),
        company_name=lead.company_name,
        contact_name=lead.contact_name,
        city=lead.city,
        region=lead.region,
        company_type=(lead.company_type.value if lead.company_type else "other"),
        specialization=lead.specialization,
        source=lead.source,
        notes=lead.notes,
    )
    data = _call_with_tool(user_prompt, _tool_cold_email(), max_tokens=800)
    return DraftEmail(
        subject=data.get("subject", "FITSIZ"),
        body_text=data.get("body_text", ""),
        reasoning=data.get("reasoning", ""),
        ai_prompt_used="cold_email",
        raw=data,
    )


def handle_reply(
    lead: Lead,
    messages: list[Message],
    incoming: Message,
) -> ReplyDraft:
    """Обрабатывает входящее письмо: классификация + ответ."""
    history = _format_history([m for m in messages if m.id != incoming.id])
    incoming_view = (
        f"Тема: {incoming.subject or '(без темы)'}\n"
        f"Текст:\n{(incoming.body_text or '').strip() or '(пусто)'}"
    )
    user_prompt = _render(
        _load_prompt("reply_handler"),
        company_name=lead.company_name,
        city=lead.city,
        contact_name=lead.contact_name,
        lead_status=lead.status.value if lead.status else "new",
        sent_documents=", ".join(_sent_documents(messages)) or "(ещё ничего)",
        conversation_history=history,
        incoming_message=incoming_view,
    )
    data = _call_with_tool(user_prompt, _tool_reply(), max_tokens=1500)
    return ReplyDraft(
        subject=data.get("reply_subject") or f"Re: {incoming.subject or 'FITSIZ'}",
        body_text=data.get("reply_text", ""),
        attachments=_filter_attachments(data.get("attachments")),
        reasoning=data.get("reasoning", ""),
        ai_prompt_used="reply_handler",
        raw=data,
        intent=data.get("intent", "question"),
        new_status=data.get("new_status", ""),
        is_warm=bool(data.get("is_warm", False)),
        should_send=bool(data.get("should_send", True)),
    )


def generate_follow_up(
    lead: Lead,
    messages: list[Message],
    stage: str,
) -> DraftEmail:
    """Генерирует follow-up (stage — 'follow_up_1' | 'follow_up_2' | 'follow_up_3')."""
    outgoing = [m for m in messages if m.direction == MessageDirection.outgoing]
    last = outgoing[-1] if outgoing else None
    last_subject = last.subject if last else "(нет)"
    days_ago: str = "—"
    if last and last.sent_at:
        delta = datetime.utcnow() - last.sent_at
        days_ago = str(max(0, delta.days))

    user_prompt = _render(
        _load_prompt("follow_up"),
        company_name=lead.company_name,
        contact_name=lead.contact_name,
        lead_status=lead.status.value if lead.status else "contacted",
        last_outgoing_subject=last_subject,
        last_outgoing_days_ago=days_ago,
        sent_documents=", ".join(_sent_documents(messages)) or "(ничего)",
        follow_up_stage=stage,
    )
    data = _call_with_tool(user_prompt, _tool_follow_up(), max_tokens=700)
    return DraftEmail(
        subject=data.get("subject") or f"Re: {last_subject}",
        body_text=data.get("body_text", ""),
        attachments=_filter_attachments(data.get("attachments")),
        reasoning=data.get("reasoning", ""),
        ai_prompt_used=f"follow_up:{stage}",
        raw=data,
    )


def qualify_lead(lead: Lead, messages: list[Message]) -> QualifierResult:
    """Проставляет оценку лида на основе переписки."""
    user_prompt = _render(
        _load_prompt("qualifier"),
        company_name=lead.company_name,
        company_type=lead.company_type.value if lead.company_type else "other",
        city=lead.city,
        specialization=lead.specialization,
        lead_status=lead.status.value if lead.status else "new",
        notes=lead.notes,
        conversation_history=_format_history(messages),
    )
    data = _call_with_tool(user_prompt, _tool_qualifier(), max_tokens=500, temperature=0.3)
    return QualifierResult(
        interest_score=int(data.get("interest_score", 5)),
        buying_readiness=int(data.get("buying_readiness", 5)),
        estimated_volume=str(data.get("estimated_volume", "unknown")),
        next_action=str(data.get("next_action", "")),
        transfer_to_manager=bool(data.get("transfer_to_manager", False)),
        reasoning=str(data.get("reasoning", "")),
        raw=data,
    )
