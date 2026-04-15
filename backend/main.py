"""FastAPI-приложение FITSIZ AI Sales Agent — точка входа."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api import leads
from backend.config import settings
from backend.database import init_db


@asynccontextmanager
async def lifespan(_: FastAPI):
    # На старте — создаём таблицы если их нет (для dev/старт без Alembic)
    init_db()
    yield


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


@app.get("/api/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "fitsiz-sales-agent"}


app.include_router(leads.router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
    )
