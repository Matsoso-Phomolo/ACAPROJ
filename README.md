# Secure Distributed Storage Security Platform

Professional MVP for the final-year project: **Secure Distributed File Storage System with Integrated Intrusion Detection**.

## What this MVP demonstrates

- User registration and login
- Encrypted file upload
- File chunking
- AES-256-GCM encryption per chunk
- SHA-256 chunk hashing
- Merkle root integrity verification
- Consistent hashing based chunk placement
- Configurable replication factor
- 5 simulated storage nodes
- Node health toggling
- Manual corruption injection
- Download-time integrity verification and replica failover
- IDS alerts for brute-force login, rate limiting, node corruption, offline-node failover, and integrity failures
- Professional dashboard with metrics, topology, file explorer, IDS center, audit logs, and academic pipeline visualization

## Run locally on Windows

```powershell
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Open:

```text
http://127.0.0.1:8000
```

## Demo steps

1. Register user `demo` with password `password123`.
2. Login.
3. Upload any file.
4. Open the file pipeline to show chunking, AES encryption, Merkle root and node distribution.
5. Corrupt a chunk on one storage node.
6. Download the file to trigger integrity verification and replica recovery.
7. Review IDS Alerts and Audit Events.
8. Toggle one node offline and download again to prove fault tolerance.

## Important note

This is an academic MVP. It simulates distributed nodes inside one backend process so the concept is easy to run during demonstration. A production version would separate coordinator, storage nodes, dashboard, database, message bus, and IDS services.


## V3 Interactive Demonstration Layer

This version adds the examiner-facing academic visualisations:

- Upload-driven KPI counters for files, logical chunks, stored replicas, healthy nodes, alerts, and storage used.
- File Explorer with file size, chunk count, replication factor, storage nodes, pipeline action, and verified download action.
- Academic System Pipeline showing upload, chunking, AES-256-GCM encryption, Merkle tree integrity, consistent hashing, IDS monitoring, and replica recovery.
- Merkle Tree Integrity View showing hash levels from chunk hashes to the trusted root.
- Consistent Hash Ring View showing physical storage nodes on a ring.
- Chunk-to-node assignment cards showing primary node and replica nodes.
- Demo controls for brute-force detection, node corruption, node offline simulation, and recovery during download.

Recommended demo:

1. Register and login.
2. Upload a PDF or text file.
3. Click **Pipeline** in File Explorer.
4. Explain the Merkle tree and hash ring visualisations.
5. Click **Corrupt One Chunk** on a node.
6. Click **Download & Verify** on the uploaded file.
7. Show IDS alerts and audit events proving detection and recovery.
8. Toggle a node offline and download again to prove fault tolerance.
