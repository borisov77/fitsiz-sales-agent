"""Настройки приложения — читаются из .env."""
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent

# Явно перезаписываем shell-окружение значениями из .env:
# иначе пустая shell-переменная (например ANTHROPIC_API_KEY='') перебивает .env.
load_dotenv(BASE_DIR / ".env", override=True)


class Settings(BaseSettings):
    """Все переменные окружения в одном объекте."""

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Email ---
    email_address: str = Field(default="", alias="EMAIL_ADDRESS")
    email_password: str = Field(default="", alias="EMAIL_PASSWORD")
    smtp_host: str = Field(default="smtp.mail.ru", alias="SMTP_HOST")
    smtp_port: int = Field(default=465, alias="SMTP_PORT")
    imap_host: str = Field(default="imap.mail.ru", alias="IMAP_HOST")
    imap_port: int = Field(default=993, alias="IMAP_PORT")

    # --- AI ---
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    ai_model: str = Field(default="claude-sonnet-4-20250514", alias="AI_MODEL")

    # --- Уведомления менеджеру (email) ---
    manager_email: str = Field(default="", alias="MANAGER_EMAIL")
    manager_name: str = Field(default="", alias="MANAGER_NAME")
    manager_email_cc: str = Field(default="", alias="MANAGER_EMAIL_CC")
    public_base_url: str = Field(
        default="http://127.0.0.1:5173", alias="PUBLIC_BASE_URL"
    )

    @property
    def manager_cc_list(self) -> list[str]:
        if not self.manager_email_cc:
            return []
        return [e.strip() for e in self.manager_email_cc.split(",") if e.strip()]

    # --- Агент ---
    agent_name: str = Field(default="Владимир", alias="AGENT_NAME")
    agent_title: str = Field(
        default="Менеджер по работе с партнёрами", alias="AGENT_TITLE"
    )
    agent_phone: str = Field(default="", alias="AGENT_PHONE")
    agent_signature: str = Field(
        default="FITSIZ | fitsiz.ru | fitsiz.app", alias="AGENT_SIGNATURE"
    )

    # --- Лимиты ---
    max_cold_emails_per_day: int = Field(default=20, alias="MAX_COLD_EMAILS_PER_DAY")
    min_delay_between_emails_sec: int = Field(
        default=180, alias="MIN_DELAY_BETWEEN_EMAILS_SEC"
    )
    max_delay_between_emails_sec: int = Field(
        default=420, alias="MAX_DELAY_BETWEEN_EMAILS_SEC"
    )
    min_reply_delay_sec: int = Field(default=900, alias="MIN_REPLY_DELAY_SEC")
    max_reply_delay_sec: int = Field(default=2700, alias="MAX_REPLY_DELAY_SEC")
    inbox_check_interval_sec: int = Field(default=600, alias="INBOX_CHECK_INTERVAL_SEC")

    # --- Режим ---
    auto_send: bool = Field(default=False, alias="AUTO_SEND")

    # --- База ---
    database_url: str = Field(
        default="sqlite:///./data/fitsiz_agent.db", alias="DATABASE_URL"
    )

    # --- API ---
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    api_cors_origins: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173",
        alias="API_CORS_ORIGINS",
    )

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.api_cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
