"""Парсинг и импорт лидов из CSV/XLSX.

Используется и HTTP-эндпоинтом `POST /api/leads/import`, и CLI-скриптом
`scripts/import_leads.py`.
"""
from __future__ import annotations

import csv
import io
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.lead import CompanyType, Lead, LeadStatus
from backend.schemas import ImportResult


# Единый формат лида: обязательны company_name, email, description.
# contact_name — необязательное (можно пустым).
EXPECTED_COLUMNS = ["company_name", "email", "description", "contact_name"]

# Образец для скачивания (GET /api/leads/csv-template).
CSV_TEMPLATE = (
    "company_name,email,description,contact_name\r\n"
    'ООО Сварка-Опт,zakaz@svarka-opt.ru,'
    '"Оптовый магазин сварочного оборудования и СИЗ, 3 точки в Казани, '
    'интересует расширение ассортимента масок",Иванов Сергей\r\n'
    'ТД Спецодежда,info@specodezhda.ru,'
    '"Розничная сеть спецодежды и СИЗ, ищут недорогие маски-хамелеоны для полки",\r\n'
)


class UnsupportedFileFormat(ValueError):
    """Бросается, если формат файла не .csv / .xlsx / .xls."""


def parse_company_type(value: str | None) -> CompanyType:
    if not value:
        return CompanyType.other
    value = value.strip().lower()
    try:
        return CompanyType(value)
    except ValueError:
        return CompanyType.other


def _normalize_row(row: dict[str, object]) -> dict[str, object]:
    """Чистим значения: strip, пустые строки → None, None-ключи выкидываем."""
    cleaned: dict[str, object] = {}
    for key, value in row.items():
        if key is None:
            continue
        k = str(key).strip()
        if isinstance(value, str):
            v = value.strip()
            cleaned[k] = v or None
        elif value is None:
            cleaned[k] = None
        else:
            cleaned[k] = value
    return cleaned


def _parse_csv(raw: bytes) -> list[dict[str, object]]:
    text = raw.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    return [_normalize_row(row) for row in reader]


def _parse_xlsx(raw: bytes) -> list[dict[str, object]]:
    # Ленивый импорт: pandas/openpyxl тяжёлые
    import pandas as pd

    df = pd.read_excel(io.BytesIO(raw), dtype=str).fillna("")
    df.columns = [str(c).strip() for c in df.columns]
    rows = df.to_dict(orient="records")
    return [_normalize_row(dict(r)) for r in rows]


def parse_file(raw: bytes, filename: str) -> list[dict[str, object]]:
    """Определяем парсер по расширению и возвращаем нормализованные строки."""
    name = (filename or "").lower()
    if name.endswith(".csv"):
        return _parse_csv(raw)
    if name.endswith((".xlsx", ".xls")):
        return _parse_xlsx(raw)
    raise UnsupportedFileFormat(f"Expected .csv or .xlsx, got: {filename!r}")


def import_rows(
    db: Session,
    rows: list[dict[str, object]],
    campaign_id: str | None = None,
) -> ImportResult:
    """Массовая вставка лидов с дедупом по email."""
    total = len(rows)
    created_ids: list[str] = []
    skipped = 0
    errors: list[str] = []

    # Один запрос вместо N+1
    existing_emails = {
        e for (e,) in db.execute(select(Lead.email)).all() if e is not None
    }

    for idx, row in enumerate(rows, start=2):  # 2 учитывает строку-заголовок
        email_val = row.get("email")
        email = (str(email_val).strip().lower()) if email_val else None

        company_val = row.get("company_name")
        company = (str(company_val).strip()) if company_val else None

        desc_val = row.get("description")
        description = (str(desc_val).strip()) if desc_val else None

        if not email or not company or not description:
            errors.append(
                f"Строка {idx}: обязательны company_name, email и description"
            )
            continue

        if email in existing_emails:
            skipped += 1
            continue

        try:
            lead = Lead(
                company_name=company,
                contact_name=row.get("contact_name"),  # type: ignore[arg-type]
                email=email,
                description=description,
                # Доп. поля поддерживаем, если они есть в файле (обратная совместимость)
                phone=row.get("phone"),  # type: ignore[arg-type]
                city=row.get("city"),  # type: ignore[arg-type]
                region=row.get("region"),  # type: ignore[arg-type]
                company_type=parse_company_type(row.get("company_type")),  # type: ignore[arg-type]
                specialization=row.get("specialization"),  # type: ignore[arg-type]
                website=row.get("website"),  # type: ignore[arg-type]
                source=row.get("source") or "csv_import",  # type: ignore[arg-type]
                notes=row.get("notes"),  # type: ignore[arg-type]
                campaign_id=campaign_id,
                status=LeadStatus.created,
                created_at=datetime.utcnow(),
            )
            db.add(lead)
            db.flush()
            created_ids.append(lead.id)
            existing_emails.add(email)
        except Exception as exc:  # pragma: no cover
            errors.append(f"Row {idx}: {exc}")

    db.commit()

    return ImportResult(
        total_rows=total,
        created=len(created_ids),
        skipped_duplicates=skipped,
        errors=errors,
        created_ids=created_ids,
    )


def import_leads_from_bytes(
    db: Session,
    raw: bytes,
    filename: str,
    campaign_id: str | None = None,
) -> ImportResult:
    """Полный пайплайн: байты файла → разбор → вставка."""
    rows = parse_file(raw, filename)
    return import_rows(db, rows, campaign_id=campaign_id)
