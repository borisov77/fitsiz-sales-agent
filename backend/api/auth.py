"""Эндпоинты входа: login / logout / me. JWT в httponly-cookie."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database import get_db
from backend.models.user import User
from backend.services import auth as auth_service

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class UserInfo(BaseModel):
    id: str
    username: str


def _set_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=settings.auth_cookie_name,
        value=token,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="lax",
        max_age=settings.jwt_expire_days * 24 * 3600,
        path="/",
    )


@router.post("/login", response_model=UserInfo)
def login(
    payload: LoginRequest,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
) -> UserInfo:
    user = auth_service.authenticate(db, payload.username, payload.password)
    if user is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, detail="Неверный логин или пароль"
        )
    token = auth_service.create_token(user)
    _set_cookie(response, token)
    return UserInfo(id=user.id, username=user.username)


@router.post("/logout")
def logout(response: Response) -> dict[str, str]:
    response.delete_cookie(settings.auth_cookie_name, path="/")
    return {"status": "logged_out"}


@router.get("/me", response_model=UserInfo)
def me(request: Request, db: Annotated[Session, Depends(get_db)]) -> UserInfo:
    token = request.cookies.get(settings.auth_cookie_name)
    payload = auth_service.decode_token(token) if token else None
    if not payload:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Не авторизован")
    user = db.get(User, payload.get("sub"))
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Пользователь не найден")
    return UserInfo(id=user.id, username=user.username)
