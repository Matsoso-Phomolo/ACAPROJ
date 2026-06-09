from __future__ import annotations

import base64
import time
import uuid
from typing import Any

from fastapi import HTTPException

from app.core.config import settings
from app.domain.models import FileRecord, StorageNode
from app.ids.engine import ids_engine
from app.services.crypto_service import (
    chunk_bytes,
    decrypt_chunk,
    encrypt_chunk,
    generate_file_key,
    merkle_root,
    sha256_hex,
)
from app.storage.cluster import ConsistentHashRing

files: dict[str, FileRecord] = {}
nodes = [StorageNode(f"node-{i}") for i in range(1, settings.node_count + 1)]
ring = ConsistentHashRing(nodes, settings.virtual_nodes)


def _format_bytes(value: int) -> str:
    units = ["B", "KB", "MB", "GB"]
    amount = float(value)
    for unit in units:
        if amount < 1024 or unit == units[-1]:
            return f"{amount:.1f} {unit}" if unit != "B" else f"{int(amount)} B"
        amount /= 1024
    return f"{value} B"


def _node_lookup(node_id: str) -> StorageNode:
    node = next((n for n in nodes if n.node_id == node_id), None)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    return node


def _merkle_levels_from_hashes(chunk_hashes: list[str]) -> list[list[str]]:
    if not chunk_hashes:
        return []
    levels: list[list[str]] = [chunk_hashes]
    current = chunk_hashes[:]
    while len(current) > 1:
        if len(current) % 2 == 1:
            current.append(current[-1])
        current = [sha256_hex((current[i] + current[i + 1]).encode()) for i in range(0, len(current), 2)]
        levels.append(current)
    return levels


def _ring_visualisation() -> list[dict[str, Any]]:
    """Return one representative virtual-node position per physical node."""
    positions: dict[str, int] = {}
    for pos, node in ring.ring:
        positions.setdefault(node.node_id, pos % 360)
    return [
        {
            "node_id": node.node_id,
            "angle": positions.get(node.node_id, 0),
            "healthy": node.healthy,
            "chunk_count": len(node.chunks),
        }
        for node in nodes
    ]


def store_file(owner: str, filename: str, raw: bytes) -> dict[str, Any]:
    started = time.perf_counter()
    file_key = generate_file_key()
    chunks = chunk_bytes(raw, settings.chunk_size_bytes)
    chunk_hashes = [sha256_hex(c) for c in chunks]
    root = merkle_root(chunk_hashes)
    file_id = str(uuid.uuid4())
    chunk_records: list[dict[str, Any]] = []

    for idx, plaintext_chunk in enumerate(chunks):
        encrypted_blob, nonce_b64 = encrypt_chunk(file_key, plaintext_chunk)
        chunk_id = sha256_hex(f"{file_id}:{idx}:{chunk_hashes[idx]}".encode())
        selected_nodes = ring.get_nodes(chunk_id, settings.replication_factor)
        for node in selected_nodes:
            node.chunks[chunk_id] = encrypted_blob
        chunk_records.append(
            {
                "index": idx,
                "chunk_id": chunk_id,
                "plain_hash": chunk_hashes[idx],
                "nonce_b64": nonce_b64,
                "nodes": [node.node_id for node in selected_nodes],
                "size": len(plaintext_chunk),
            }
        )

    record = FileRecord(
        file_id=file_id,
        owner=owner,
        filename=filename or "uploaded-file",
        size=len(raw),
        merkle_root=root,
        file_key_b64=base64.b64encode(file_key).decode(),
        chunks=chunk_records,
        created_at=time.time(),
    )
    files[file_id] = record
    elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
    ids_engine.add_event("upload", f"{owner} uploaded {record.filename}", file_id=file_id)
    ids_engine.add_event("encryption", f"AES-256-GCM encrypted {len(chunks)} chunks for {record.filename}", file_id=file_id)
    ids_engine.add_event("distribution", f"Chunks distributed with RF={settings.replication_factor} using consistent hashing", file_id=file_id)
    return {
        "file_id": file_id,
        "filename": record.filename,
        "size": record.size,
        "size_human": _format_bytes(record.size),
        "chunks": len(chunks),
        "replication_factor": settings.replication_factor,
        "merkle_root": root,
        "elapsed_ms": elapsed_ms,
    }


def list_user_files(owner: str) -> list[dict[str, Any]]:
    result = []
    for f in files.values():
        if f.owner != owner:
            continue
        node_ids = sorted({node_id for chunk in f.chunks for node_id in chunk["nodes"]})
        result.append(
            {
                "file_id": f.file_id,
                "filename": f.filename,
                "size": f.size,
                "size_human": _format_bytes(f.size),
                "chunks": len(f.chunks),
                "replicas": settings.replication_factor,
                "node_distribution": node_ids,
                "merkle_root": f.merkle_root,
                "created_at": f.created_at,
                "status": "Integrity Protected",
            }
        )
    return result


def reconstruct_file(file_id: str, username: str) -> tuple[bytes, str]:
    if file_id not in files:
        raise HTTPException(status_code=404, detail="File not found")
    record = files[file_id]
    if record.owner != username:
        raise HTTPException(status_code=403, detail="Access denied")

    file_key = base64.b64decode(record.file_key_b64)
    restored_chunks: list[bytes] = []
    recovered_hashes: list[str] = []

    for chunk in sorted(record.chunks, key=lambda c: c["index"]):
        recovered = None
        last_error = None
        for node_id in chunk["nodes"]:
            node = _node_lookup(node_id)
            if not node.healthy:
                ids_engine.add_event("failover", f"Skipped offline node {node.node_id}; trying replica", "medium", node_id=node.node_id, file_id=file_id)
                continue
            blob = node.chunks.get(chunk["chunk_id"])
            if blob is None:
                continue
            try:
                plaintext = decrypt_chunk(file_key, blob)
                if sha256_hex(plaintext) != chunk["plain_hash"]:
                    node.corruptions += 1
                    ids_engine.add_event("integrity", f"Chunk hash verification failed on {node.node_id}", "high", node_id=node.node_id, file_id=file_id)
                    continue
                recovered = plaintext
                break
            except Exception as exc:
                node.corruptions += 1
                last_error = str(exc)
                ids_engine.add_event("integrity", f"AES-GCM authentication failed on {node.node_id}", "high", node_id=node.node_id, file_id=file_id)
        if recovered is None:
            raise HTTPException(status_code=500, detail=f"Could not recover chunk {chunk['index']}: {last_error}")
        restored_chunks.append(recovered)
        recovered_hashes.append(sha256_hex(recovered))

    if merkle_root(recovered_hashes) != record.merkle_root:
        ids_engine.add_event("integrity", f"Merkle root mismatch for file {file_id}", "critical", file_id=file_id)
        raise HTTPException(status_code=500, detail="Merkle root verification failed")

    content = b"".join(restored_chunks)
    ids_engine.add_event("download", f"{username} downloaded {record.filename}; Merkle root verified", file_id=file_id)
    return content, record.filename


def corrupt_node_chunk(node_id: str) -> dict[str, str]:
    node = _node_lookup(node_id)
    if not node.chunks:
        raise HTTPException(status_code=400, detail="Node has no chunks to corrupt")
    chunk_id = next(iter(node.chunks.keys()))
    blob = bytearray(node.chunks[chunk_id])
    if blob:
        blob[-1] ^= 0xFF
    node.chunks[chunk_id] = bytes(blob)
    node.corruptions += 1
    ids_engine.add_event("node_corruption", f"Manual corruption injected into {node_id}", "medium", node_id=node_id, chunk_id=chunk_id)
    return {"message": "chunk corrupted", "node_id": node_id, "chunk_id": chunk_id}


def toggle_node_health(node_id: str) -> dict[str, Any]:
    node = _node_lookup(node_id)
    node.healthy = not node.healthy
    severity = "medium" if not node.healthy else "info"
    ids_engine.add_event("node_health", f"{node_id} set to {'Healthy' if node.healthy else 'Offline'}", severity, node_id=node_id)
    return {"node_id": node_id, "healthy": node.healthy}


def file_pipeline(file_id: str, username: str) -> dict[str, Any]:
    if file_id not in files:
        raise HTTPException(status_code=404, detail="File not found")
    record = files[file_id]
    if record.owner != username:
        raise HTTPException(status_code=403, detail="Access denied")

    chunk_hashes = [c["plain_hash"] for c in sorted(record.chunks, key=lambda c: c["index"])]
    merkle_levels = _merkle_levels_from_hashes(chunk_hashes)
    assignments = [
        {
            "chunk_index": c["index"],
            "chunk_id": c["chunk_id"][:16] + "...",
            "primary_node": c["nodes"][0] if c["nodes"] else "none",
            "replica_nodes": c["nodes"][1:],
            "all_nodes": c["nodes"],
        }
        for c in sorted(record.chunks, key=lambda c: c["index"])
    ]
    return {
        "file_id": record.file_id,
        "filename": record.filename,
        "size": record.size,
        "size_human": _format_bytes(record.size),
        "chunk_size": settings.chunk_size_bytes,
        "replication_factor": settings.replication_factor,
        "merkle_root": record.merkle_root,
        "steps": [
            {"name": "1. File Upload", "detail": f"{record.filename} received by the client layer."},
            {"name": "2. Chunking", "detail": f"File split into {len(record.chunks)} logical chunks of up to {settings.chunk_size_bytes} bytes."},
            {"name": "3. AES-256-GCM Encryption", "detail": "Each chunk encrypted independently with authenticated encryption and a unique nonce."},
            {"name": "4. SHA-256 + Merkle Tree", "detail": "Chunk hashes are combined upward to produce one trusted Merkle root."},
            {"name": "5. Consistent Hash Routing", "detail": f"Each chunk ID is mapped to nodes on a hash ring with replication factor {settings.replication_factor}."},
            {"name": "6. IDS Monitoring", "detail": "Authentication failures, node corruption, offline nodes, and integrity failures are logged as security events."},
            {"name": "7. Replica Recovery", "detail": "During download, corrupted/offline replicas are skipped and healthy replicas are used."},
        ],
        "chunks": [
            {
                "index": c["index"],
                "chunk_id": c["chunk_id"][:16] + "...",
                "hash": c["plain_hash"][:16] + "...",
                "full_hash": c["plain_hash"],
                "size": c["size"],
                "nodes": c["nodes"],
                "primary": c["nodes"][0] if c["nodes"] else "none",
                "replicas": c["nodes"][1:],
            }
            for c in sorted(record.chunks, key=lambda c: c["index"])
        ],
        "merkle_tree": {
            "root": record.merkle_root,
            "levels": [
                [h[:16] + "..." for h in level]
                for level in merkle_levels
            ],
        },
        "hash_ring": {
            "nodes": _ring_visualisation(),
            "assignments": assignments,
        },
    }


def cluster_status() -> dict[str, Any]:
    total_chunks = sum(len(n.chunks) for n in nodes)
    unique_chunks = len({chunk_id for n in nodes for chunk_id in n.chunks})
    total_bytes = sum(f.size for f in files.values())
    healthy_nodes = sum(1 for n in nodes if n.healthy)
    return {
        "nodes": [
            {
                "node_id": n.node_id,
                "healthy": n.healthy,
                "status": "Healthy" if n.healthy else "Offline",
                "chunk_count": len(n.chunks),
                "corruptions": n.corruptions,
            }
            for n in nodes
        ],
        "metrics": {
            "files": len(files),
            "logical_chunks": unique_chunks,
            "stored_replicas": total_chunks,
            "healthy_nodes": healthy_nodes,
            "total_nodes": len(nodes),
            "storage_used": total_bytes,
            "storage_used_human": _format_bytes(total_bytes),
            "alerts": len(ids_engine.alerts),
            "events": len(ids_engine.events),
            "replication_factor": settings.replication_factor,
        },
        "file_count": len(files),
        "alert_count": len(ids_engine.alerts),
        "event_count": len(ids_engine.events),
        "topology": {"coordinator": "coordinator-1", "nodes": [n.node_id for n in nodes], "ring": _ring_visualisation()},
    }


def demo_flow() -> dict[str, Any]:
    return {
        "title": "Final-Year Demonstration Flow",
        "flow": [
            "Register and login as a user.",
            "Upload a file and watch it become encrypted chunks.",
            "Open the Academic Pipeline to show AES-GCM, Merkle tree, hash ring, chunk IDs, and node assignments.",
            "Corrupt one chunk on a node to simulate malicious storage behaviour.",
            "Download the file to trigger integrity verification and automatic replica failover.",
            "Review IDS alerts and audit events.",
            "Toggle a node offline and repeat download to prove fault tolerance.",
        ],
    }
