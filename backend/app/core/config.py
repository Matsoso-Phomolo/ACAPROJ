from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    app_name: str = "Secure Distributed File Storage + IDS MVP"
    app_secret: str = os.environ.get("APP_SECRET", "dev-secret-change-me")
    jwt_algorithm: str = "HS256"
    jwt_expires_seconds: int = int(os.environ.get("JWT_EXPIRES_SECONDS", "3600"))
    chunk_size_bytes: int = int(os.environ.get("CHUNK_SIZE_BYTES", str(256 * 1024)))
    replication_factor: int = int(os.environ.get("REPLICATION_FACTOR", "2"))
    node_count: int = int(os.environ.get("NODE_COUNT", "5"))
    virtual_nodes: int = int(os.environ.get("VIRTUAL_NODES", "30"))
    brute_force_threshold: int = int(os.environ.get("BRUTE_FORCE_THRESHOLD", "5"))
    brute_force_window_seconds: int = int(os.environ.get("BRUTE_FORCE_WINDOW_SECONDS", "60"))
    rate_limit_capacity: float = float(os.environ.get("RATE_LIMIT_CAPACITY", "30"))
    rate_limit_refill_per_second: float = float(os.environ.get("RATE_LIMIT_REFILL_PER_SECOND", "5"))


settings = Settings()
