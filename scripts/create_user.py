#!/usr/bin/env python3
"""Создание пользователя для входа в дашборд.

Запрашивает логин и пароль в терминале, сохраняет с bcrypt-хешем.
Пароль нигде не хранится в открытом виде и не передаётся аргументом.

Запуск:
    python scripts/create_user.py
"""
from __future__ import annotations

import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.database import SessionLocal, init_db  # noqa: E402
from backend.services import auth as auth_service  # noqa: E402


def main() -> int:
    init_db()  # гарантируем, что таблица users существует

    username = input("Логин: ").strip()
    if not username:
        print("Логин не может быть пустым.")
        return 1

    with SessionLocal() as db:
        if auth_service.get_user_by_username(db, username):
            print(f"Пользователь '{username}' уже существует.")
            return 1

        password = getpass.getpass("Пароль: ")
        if len(password) < 6:
            print("Пароль слишком короткий (минимум 6 символов).")
            return 1
        confirm = getpass.getpass("Повторите пароль: ")
        if password != confirm:
            print("Пароли не совпадают.")
            return 1

        user = auth_service.create_user(db, username, password)
        print(f"Пользователь '{user.username}' создан. Можно входить в дашборд.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
