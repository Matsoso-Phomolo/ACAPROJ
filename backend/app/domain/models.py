from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class StorageNode:
    node_id: str
    healthy: bool = True
    chunks: dict[str, bytes] = field(default_factory=dict)
    corruptions: int = 0


@dataclass
class FileRecord:
    file_id: str
    owner: str
    filename: str
    size: int
    merkle_root: str
    file_key_b64: str
    chunks: list[dict[str, Any]]
    created_at: float
