from __future__ import annotations

import hashlib
from bisect import bisect_right

from fastapi import HTTPException

from app.domain.models import StorageNode


class ConsistentHashRing:
    def __init__(self, storage_nodes: list[StorageNode], virtual_nodes: int = 30):
        self.virtual_nodes = virtual_nodes
        self.ring: list[tuple[int, StorageNode]] = []
        for node in storage_nodes:
            self.add_node(node)

    def _hash(self, value: str) -> int:
        return int(hashlib.sha256(value.encode()).hexdigest(), 16)

    def add_node(self, node: StorageNode) -> None:
        for i in range(self.virtual_nodes):
            self.ring.append((self._hash(f"{node.node_id}:{i}"), node))
        self.ring.sort(key=lambda item: item[0])

    def get_nodes(self, key: str, count: int) -> list[StorageNode]:
        healthy_entries = [(pos, node) for pos, node in self.ring if node.healthy]
        if not healthy_entries:
            raise HTTPException(status_code=503, detail="No healthy storage nodes available")

        unique_healthy_count = len({node.node_id for _, node in healthy_entries})
        positions = [pos for pos, _ in healthy_entries]
        start = bisect_right(positions, self._hash(key)) % len(healthy_entries)
        selected: list[StorageNode] = []
        seen: set[str] = set()
        idx = start

        while len(selected) < min(count, unique_healthy_count):
            node = healthy_entries[idx][1]
            if node.node_id not in seen:
                selected.append(node)
                seen.add(node.node_id)
            idx = (idx + 1) % len(healthy_entries)

        return selected
