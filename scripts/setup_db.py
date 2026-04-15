"""Инициализация БД: создаёт все таблицы из моделей.

Использование:
    python -m scripts.setup_db
"""
from __future__ import annotations

import sys
from pathlib import Path

# Добавляем корень проекта в sys.path для прямого запуска
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.database import DATABASE_URL, init_db  # noqa: E402


def main() -> None:
    print(f"Инициализация БД: {DATABASE_URL}")
    init_db()
    print("Таблицы созданы (если отсутствовали).")


if __name__ == "__main__":
    main()
