"""Симметричное шифрование секретов at-rest (Fernet).

Используется для AI-токена, который хранится в app_settings ТОЛЬКО зашифрованным.
Ключ — FITSIZ_SECRET_KEY из .env (urlsafe-base64, 32 байта; сгенерировать:
`python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`).

Безопасность: ни plaintext, ни ключ НИКОГДА не попадают в текст исключений/логов.
"""
from __future__ import annotations

from backend.config import settings


class CryptoError(RuntimeError):
    """Ошибка шифрования/дешифрования. Текст НЕ содержит секретов."""


class SecretKeyMissing(CryptoError):
    """FITSIZ_SECRET_KEY не задан или некорректен."""


def is_configured() -> bool:
    """True, если ключ шифрования задан и валиден (можно хранить секреты в БД)."""
    try:
        _fernet()
        return True
    except CryptoError:
        return False


def _fernet():
    key = settings.fitsiz_secret_key
    if not key:
        raise SecretKeyMissing(
            "FITSIZ_SECRET_KEY не задан в .env — хранение AI-токена в БД недоступно"
        )
    try:
        from cryptography.fernet import Fernet
    except ImportError as exc:  # pragma: no cover
        raise CryptoError("пакет cryptography не установлен") from exc
    try:
        return Fernet(key.encode() if isinstance(key, str) else key)
    except Exception as exc:  # noqa: BLE001 — некорректный формат ключа
        # НЕ прокидываем исходный текст: он может содержать фрагмент ключа.
        raise SecretKeyMissing("FITSIZ_SECRET_KEY имеет неверный формат") from None


def encrypt(plaintext: str) -> str:
    """plaintext → шифртекст (str). Бросает CryptoError без раскрытия значения."""
    f = _fernet()
    try:
        return f.encrypt(plaintext.encode("utf-8")).decode("ascii")
    except Exception:  # noqa: BLE001
        raise CryptoError("не удалось зашифровать значение") from None


def decrypt(token: str) -> str:
    """шифртекст → plaintext (str). Бросает CryptoError без раскрытия значения."""
    f = _fernet()
    try:
        return f.decrypt(token.encode("ascii")).decode("utf-8")
    except Exception:  # noqa: BLE001 — InvalidToken и пр.
        raise CryptoError("не удалось расшифровать значение") from None
