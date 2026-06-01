"""Управление двумя документами агента (прайс-лист + презентация) через UI."""
from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from pydantic import BaseModel

from backend.services import document_store as ds

router = APIRouter(prefix="/api/documents", tags=["documents"])


class SlotStatus(BaseModel):
    key: str
    type: str
    title: str
    filename: str
    send_when: str
    format_label: str
    accept: list[str]
    uploaded: bool
    uploaded_at: str | None = None


class DocumentsStatus(BaseModel):
    slots: dict[str, SlotStatus]
    any_empty: bool


def _spec_or_404(slot_key: str) -> ds.SlotSpec:
    spec = ds.SLOTS.get(slot_key)
    if spec is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"Неизвестный слот: {slot_key}")
    return spec


# ==========================
# Статус обоих слотов
# ==========================
@router.get("", response_model=DocumentsStatus)
def get_documents() -> Any:
    return ds.all_slots_status()


# ==========================
# Загрузка / замена
# ==========================
def _handle_upload(slot_key: str, file: UploadFile) -> Any:
    spec = _spec_or_404(slot_key)
    data = file.file.read()
    try:
        return ds.save_upload(spec, file.filename or "", data)
    except ds.DocumentError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/upload/pricelist", response_model=SlotStatus)
def upload_pricelist(file: Annotated[UploadFile, File(...)]) -> Any:
    return _handle_upload("pricelist", file)


@router.post("/upload/presentation", response_model=SlotStatus)
def upload_presentation(file: Annotated[UploadFile, File(...)]) -> Any:
    return _handle_upload("presentation", file)


# ==========================
# Удаление
# ==========================
@router.delete("/pricelist", response_model=SlotStatus)
def delete_pricelist() -> Any:
    return ds.delete_slot(_spec_or_404("pricelist"))


@router.delete("/presentation", response_model=SlotStatus)
def delete_presentation() -> Any:
    return ds.delete_slot(_spec_or_404("presentation"))
