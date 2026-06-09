from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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

# CORS FOR VERCEL FRONTEND
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://acaproj.vercel.app",
        "https://acaproj.onrender.com",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(RateLimitMiddleware)

app.include_router(router)

APP_DIR = Path(__file__).resolve().parent
STATIC_DIR = APP_DIR.parent / "frontend" / "static"

if not STATIC_DIR.exists():
    STATIC_DIR = Path("/app/frontend/static")

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", response_class=HTMLResponse)
def home():
    index_file = STATIC_DIR / "index.html"

    if index_file.exists():
        return index_file.read_text(encoding="utf-8")

    return """
    <html>
        <body>
            <h1>Secure Distributed Storage Security Platform</h1>
            <p>Backend running successfully.</p>
        </body>
    </html>
    """


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": "0.3.0",
    }


@app.get("/healthz")
def healthz():
    return {"status": "ok"}