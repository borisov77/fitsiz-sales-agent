"""FastAPI-приложение FITSIZ AI Sales Agent — точка входа."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.api import auth as auth_api
from backend.api import campaign
from backend.api import conversations
from backend.api import documents
from backend.api import email as email_api
from backend.api import leads
from backend.api import settings as settings_api
from backend.config import settings
from backend.database import init_db


@asynccontextmanager
async def lifespan(_: FastAPI):
    import logging
    logging.basicConfig(level=logging.INFO)

    # На старте — создаём таблицы если их нет (для dev/старт без Alembic)
    init_db()

    # Запускаем фоновый планировщик (IMAP-check, send-queued, follow-up)
    from backend.services.scheduler import start_scheduler, stop_scheduler
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(
    title="FITSIZ AI Sales Agent",
    description="Автономный AI-агент для холодных B2B-продаж сварочных масок FITSIZ.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Пути под /api, доступные без аутентификации
_PUBLIC_PATHS = {"/api/health", "/api/auth/login"}


@app.middleware("http")
async def auth_guard(request: Request, call_next):
    """Защищает все /api-эндпоинты: без валидного JWT-cookie → 401.

    Исключения: health-check, login и CORS-preflight (OPTIONS).
    """
    path = request.url.path
    if (
        request.method == "OPTIONS"
        or not path.startswith("/api/")
        or path in _PUBLIC_PATHS
    ):
        return await call_next(request)

    from backend.services.auth import decode_token

    token = request.cookies.get(settings.auth_cookie_name)
    if not token or decode_token(token) is None:
        return JSONResponse(
            status_code=401, content={"detail": "Требуется вход в систему"}
        )
    return await call_next(request)


@app.get("/api/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "fitsiz-sales-agent"}


app.include_router(leads.router)
app.include_router(email_api.router)
app.include_router(conversations.router)
app.include_router(documents.router)
app.include_router(settings_api.router)
app.include_router(campaign.router)
app.include_router(auth_api.router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
    )
