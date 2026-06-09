from __future__ import annotations

import time
from typing import Any

import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext

from app.core.config import settings
from app.ids.engine import ids_engine

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login")
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

users: dict[str, dict[str, Any]] = {}


def sign_token(username: str) -> str:
    payload = {"sub": username, "exp": int(time.time()) + settings.jwt_expires_seconds}
    return jwt.encode(payload, settings.app_secret, algorithm=settings.jwt_algorithm)


def register_user(username: str, password: str) -> None:
    username = username.strip().lower()
    if not username or len(password) < 6:
        raise HTTPException(status_code=400, detail="Username required and password must be at least 6 characters")
    if username in users:
        raise HTTPException(status_code=409, detail="User already exists")
    users[username] = {"password_hash": pwd_context.hash(password), "created_at": time.time()}
    ids_engine.add_event("auth", f"User registered: {username}")


def authenticate_user(username: str, password: str, request: Request) -> str:
    username = username.strip().lower()
    ip = request.client.host if request.client else "unknown"
    if username not in users or not pwd_context.verify(password, users[username]["password_hash"]):
        ids_engine.record_failed_login(ip)
        raise HTTPException(status_code=401, detail="Invalid credentials")
    ids_engine.clear_failed_logins(ip)
    ids_engine.add_event("auth", f"User logged in: {username}")
    return sign_token(username)


def current_user(token: str = Depends(oauth2_scheme)) -> str:
    try:
        payload = jwt.decode(token, settings.app_secret, algorithms=[settings.jwt_algorithm])
        username = payload.get("sub")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    if username not in users:
        raise HTTPException(status_code=401, detail="Unknown user")
    return username
