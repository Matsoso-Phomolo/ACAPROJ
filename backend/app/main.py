from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.core.config import settings
from app.ids.engine import RateLimitMiddleware

app = FastAPI(
    title=settings.app_name,
    description="Professional MVP for a Secure Distributed File Storage System with Integrated IDS.",
    version="0.3.0",
)
app.add_middleware(RateLimitMiddleware)
app.include_router(router)

# backend/app/main.py -> backend -> project root
BASE_DIR = Path(__file__).resolve().parents[2]
STATIC_DIR = BASE_DIR / "frontend" / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", response_class=HTMLResponse)
def home():
    return (STATIC_DIR / "index.html").read_text(encoding="utf-8")


@app.get("/health")
def health():
    return {"status": "ok", "service": settings.app_name, "version": "0.3.0"}

@app.get("/healthz")
def healthz():
    return {"status": "ok"}