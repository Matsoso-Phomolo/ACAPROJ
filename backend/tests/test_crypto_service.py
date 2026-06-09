from app.services.crypto_service import chunk_bytes, decrypt_chunk, encrypt_chunk, generate_file_key, merkle_root, sha256_hex


def test_encrypt_decrypt_round_trip():
    key = generate_file_key()
    plaintext = b"Final year secure storage MVP"
    encrypted, _ = encrypt_chunk(key, plaintext)
    assert encrypted != plaintext
    assert decrypt_chunk(key, encrypted) == plaintext


def test_merkle_root_is_deterministic():
    chunks = chunk_bytes(b"abcdef", 2)
    hashes = [sha256_hex(c) for c in chunks]
    assert merkle_root(hashes) == merkle_root(hashes)
