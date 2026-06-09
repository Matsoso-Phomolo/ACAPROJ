# System Architecture Overview

## Purpose

This MVP demonstrates a secure distributed file storage system with integrated intrusion detection. It is intentionally lightweight, but it is structured to resemble the full final-year project architecture.

## Main Components

1. **Client/UI Layer** — browser dashboard for registration, login, file upload, file download, IDS alerts, and node simulation.
2. **Coordinator API** — FastAPI backend that authenticates users, routes chunks, manages file metadata, and exposes monitoring endpoints.
3. **Storage Cluster Simulation** — five in-memory storage nodes that hold encrypted chunks only.
4. **Crypto Service** — chunking, AES-GCM encryption, SHA-256 hashing, and Merkle root verification.
5. **IDS Engine** — detects brute-force attempts, API rate abuse, corrupted chunks, and storage-node integrity failures.

## MVP Security Note

The MVP stores the file key in memory so the demo can download files easily. In the full dissertation system, key handling should move to a stronger client-side model with per-user encrypted file keys and persistent database-backed metadata.
