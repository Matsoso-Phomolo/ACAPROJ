from __future__ import annotations

import base64
import hashlib
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def chunk_bytes(data: bytes, size: int) -> list[bytes]:
    return [data[i : i + size] for i in range(0, len(data), size)] or [b""]


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def merkle_root(chunk_hashes: list[str]) -> str:
    if not chunk_hashes:
        return sha256_hex(b"")
    level = chunk_hashes[:]
    while len(level) > 1:
        if len(level) % 2 == 1:
            level.append(level[-1])
        level = [sha256_hex((level[i] + level[i + 1]).encode()) for i in range(0, len(level), 2)]
    return level[0]


def generate_file_key() -> bytes:
    return AESGCM.generate_key(bit_length=256)


def encrypt_chunk(file_key: bytes, plaintext: bytes) -> tuple[bytes, str]:
    nonce = os.urandom(12)
    encrypted = AESGCM(file_key).encrypt(nonce, plaintext, None)
    return nonce + encrypted, base64.b64encode(nonce).decode()


def decrypt_chunk(file_key: bytes, encrypted_blob: bytes) -> bytes:
    nonce, ciphertext = encrypted_blob[:12], encrypted_blob[12:]
    return AESGCM(file_key).decrypt(nonce, ciphertext, None)
