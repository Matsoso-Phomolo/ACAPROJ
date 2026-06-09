from __future__ import annotations

import time
import uuid
from collections import defaultdict, deque
from typing import Any

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings


class IDSEngine:
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []
        self.alerts: list[dict[str, Any]] = []
        self.failed_logins: dict[str, deque[float]] = defaultdict(deque)
        self.request_buckets: dict[str, dict[str, float]] = defaultdict(
            lambda: {"tokens": settings.rate_limit_capacity, "last": time.time()}
        )

    def now_ms(self) -> int:
        return int(time.time() * 1000)

    def add_event(self, kind: str, message: str, severity: str = "info", **extra: Any) -> None:
        event = {
            "id": str(uuid.uuid4()),
            "time": self.now_ms(),
            "kind": kind,
            "severity": severity,
            "message": message,
            **extra,
        }
        self.events.append(event)
        if severity in {"medium", "high", "critical"}:
            self.alerts.append(event)

    def record_failed_login(self, ip: str) -> None:
        q = self.failed_logins[ip]
        current = time.time()
        q.append(current)
        while q and q[0] < current - settings.brute_force_window_seconds:
            q.popleft()
        if len(q) >= settings.brute_force_threshold:
            self.add_event(
                "bruteforce",
                f"Possible brute-force attack from {ip}",
                "high",
                ip=ip,
                failed_attempts=len(q),
            )

    def clear_failed_logins(self, ip: str) -> None:
        self.failed_logins[ip].clear()

    def check_rate_limit(self, ip: str) -> None:
        bucket = self.request_buckets[ip]
        current = time.time()
        elapsed = current - bucket["last"]
        bucket["tokens"] = min(settings.rate_limit_capacity, bucket["tokens"] + elapsed * settings.rate_limit_refill_per_second)
        bucket["last"] = current
        if bucket["tokens"] < 1:
            self.add_event("rate_limit", f"Rate limit exceeded by {ip}", "medium", ip=ip)
            raise HTTPException(status_code=429, detail="Too many requests")
        bucket["tokens"] -= 1


ids_engine = IDSEngine()


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        ip = request.client.host if request.client else "unknown"
        if request.url.path.startswith("/api"):
            ids_engine.check_rate_limit(ip)
        return await call_next(request)
