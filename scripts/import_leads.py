"""CLI-импорт лидов из CSV/XLSX в БД (без запуска FastAPI).

Использование:
    python -m scripts.import_leads --file path/to/leads.csv
    python -m scripts.import_leads --file leads.xlsx --campaign-id <uuid>
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Корень проекта в sys.path для прямого запуска
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.database import SessionLocal, init_db  # noqa: E402
from backend.services.lead_importer import (  # noqa: E402
    UnsupportedFileFormat,
    import_leads_from_bytes,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Импорт лидов FITSIZ из CSV/XLSX"
    )
    parser.add_argument(
        "--file",
        "-f",
        required=True,
        help="Путь к CSV или XLSX-файлу с лидами",
    )
    parser.add_argument(
        "--campaign-id",
        "-c",
        default=None,
        help="UUID кампании, к которой привязать лидов (опционально)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    path = Path(args.file).expanduser().resolve()

    if not path.exists():
        print(f"[ERROR] Файл не найден: {path}", file=sys.stderr)
        return 2

    # Убеждаемся, что таблицы существуют
    init_db()

    raw = path.read_bytes()

    with SessionLocal() as db:
        try:
            result = import_leads_from_bytes(
                db, raw, path.name, campaign_id=args.campaign_id
            )
        except UnsupportedFileFormat as exc:
            print(f"[ERROR] {exc}", file=sys.stderr)
            return 2

    print("=" * 50)
    print(f"Файл:              {path.name}")
    print(f"Всего строк:       {result.total_rows}")
    print(f"Создано лидов:     {result.created}")
    print(f"Пропущено дублей:  {result.skipped_duplicates}")
    if result.errors:
        print(f"Ошибок:            {len(result.errors)}")
        for err in result.errors[:20]:
            print(f"  - {err}")
        if len(result.errors) > 20:
            print(f"  ... ещё {len(result.errors) - 20}")
    print("=" * 50)
    return 0


if __name__ == "__main__":
    sys.exit(main())
