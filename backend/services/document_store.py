"""Хранилище двух фиксированных документов агента: прайс-лист и презентация.

Агент работает РОВНО с двумя файлами. Источник истины — `documents/documents.json`
(описание слотов) + реальные файлы в `documents/`. Никакого ручного копирования:
загрузка/замена/удаление идёт только через API (`backend/api/documents.py`).

Слот считается «заполненным», только если файл физически лежит на диске. Запись
есть в json, но файла нет → агент его не предложит (см. `available_attachments`).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from backend.config import BASE_DIR

DOCUMENTS_DIR = BASE_DIR / "documents"
MANIFEST_PATH = DOCUMENTS_DIR / "documents.json"

MAX_UPLOAD_BYTES = 20 * 1024 * 1024  # 20 МБ


@dataclass(frozen=True)
class SlotSpec:
    """Жёстко заданный слот. Других типов документов не существует."""

    key: str                 # ключ слота в API ("pricelist" | "presentation")
    filename: str            # каноническое имя файла на диске (перезаписывается)
    doc_type: str            # значение поля "type" в documents.json
    title: str
    send_when: str
    extensions: tuple[str, ...]
    format_label: str


SLOTS: dict[str, SlotSpec] = {
    "pricelist": SlotSpec(
        key="pricelist",
        filename="pricelist_fitsiz_2026.xlsx",
        doc_type="pricelist",
        title="Оптовый прайс-лист FITSIZ",
        send_when="клиент спрашивает про цены, опт, скидки, стоимость, условия закупки",
        extensions=(".xls", ".xlsx"),
        format_label="формат Excel (.xls, .xlsx)",
    ),
    "presentation": SlotSpec(
        key="presentation",
        filename="presentation_fitsiz.pdf",
        doc_type="presentation",
        title="Презентация FITSIZ",
        send_when="клиент хочет узнать о компании, продукции, ассортименте, первое знакомство",
        extensions=(".pdf",),
        format_label="формат PDF",
    ),
}


class DocumentError(RuntimeError):
    """Ошибка валидации/IO при работе с документами."""


# ==========================
# Манифест documents.json
# ==========================
def _default_manifest() -> list[dict[str, Any]]:
    return [
        {
            "filename": s.filename,
            "type": s.doc_type,
            "title": s.title,
            "send_when": s.send_when,
            "uploaded_at": None,
        }
        for s in SLOTS.values()
    ]


def load_manifest() -> list[dict[str, Any]]:
    """Читает documents.json. Если файла нет/битый — восстанавливает дефолт."""
    if not MANIFEST_PATH.is_file():
        save_manifest(_default_manifest())
    try:
        data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            raise ValueError("ожидался список")
        return data
    except (json.JSONDecodeError, ValueError):
        default = _default_manifest()
        save_manifest(default)
        return default


def save_manifest(records: list[dict[str, Any]]) -> None:
    DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(
        json.dumps(records, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _record_for(spec: SlotSpec, manifest: list[dict[str, Any]]) -> dict[str, Any]:
    for rec in manifest:
        if rec.get("type") == spec.doc_type:
            return rec
    rec = {
        "filename": spec.filename,
        "type": spec.doc_type,
        "title": spec.title,
        "send_when": spec.send_when,
        "uploaded_at": None,
    }
    manifest.append(rec)
    return rec


# ==========================
# Статус слотов
# ==========================
def slot_status(spec: SlotSpec, manifest: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    manifest = manifest if manifest is not None else load_manifest()
    rec = _record_for(spec, manifest)
    path = DOCUMENTS_DIR / spec.filename
    uploaded = path.is_file()
    return {
        "key": spec.key,
        "type": spec.doc_type,
        "title": spec.title,
        "filename": spec.filename,
        "send_when": spec.send_when,
        "format_label": spec.format_label,
        "accept": list(spec.extensions),
        "uploaded": uploaded,
        "uploaded_at": rec.get("uploaded_at") if uploaded else None,
    }


def all_slots_status() -> dict[str, Any]:
    manifest = load_manifest()
    slots = {key: slot_status(spec, manifest) for key, spec in SLOTS.items()}
    any_empty = any(not s["uploaded"] for s in slots.values())
    return {"slots": slots, "any_empty": any_empty}


# ==========================
# Загрузка / удаление
# ==========================
def _validate(spec: SlotSpec, original_filename: str, data: bytes) -> None:
    ext = Path(original_filename or "").suffix.lower()
    if ext not in spec.extensions:
        allowed = ", ".join(spec.extensions)
        raise DocumentError(
            f"Недопустимый формат «{ext or '—'}» для слота «{spec.title}». "
            f"Разрешено: {allowed}."
        )
    if len(data) == 0:
        raise DocumentError("Файл пустой.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise DocumentError(
            f"Файл больше {MAX_UPLOAD_BYTES // (1024 * 1024)} МБ "
            f"({len(data) // (1024 * 1024)} МБ)."
        )


def save_upload(spec: SlotSpec, original_filename: str, data: bytes, *, now: datetime | None = None) -> dict[str, Any]:
    """Валидирует и сохраняет файл под каноническим именем, обновляет дату в json."""
    _validate(spec, original_filename, data)
    DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
    (DOCUMENTS_DIR / spec.filename).write_bytes(data)

    manifest = load_manifest()
    rec = _record_for(spec, manifest)
    rec["uploaded_at"] = (now or datetime.utcnow()).isoformat()
    save_manifest(manifest)
    return slot_status(spec, manifest)


def delete_slot(spec: SlotSpec) -> dict[str, Any]:
    """Удаляет файл слота и сбрасывает дату загрузки."""
    path = DOCUMENTS_DIR / spec.filename
    if path.is_file():
        path.unlink()
    manifest = load_manifest()
    rec = _record_for(spec, manifest)
    rec["uploaded_at"] = None
    save_manifest(manifest)
    return slot_status(spec, manifest)


# ==========================
# Для AI-движка
# ==========================
def available_attachments() -> set[str]:
    """Имена файлов из манифеста, которые РЕАЛЬНО есть на диске."""
    manifest = load_manifest()
    out: set[str] = set()
    for rec in manifest:
        name = rec.get("filename")
        if name and (DOCUMENTS_DIR / name).is_file():
            out.add(name)
    return out
