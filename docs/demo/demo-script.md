# Demo Script

1. Start the backend.
2. Open `http://127.0.0.1:8000`.
3. Register user `demo` with password `password123`.
4. Login and upload any small file.
5. Observe the file ID, chunk count, Merkle root, and node chunk distribution.
6. Download the file to prove reconstruction works.
7. Press **Trigger Failed Login** five times to generate a brute-force IDS alert.
8. Press **Corrupt One Chunk** on a node that has chunks.
9. Download the file again and observe integrity alerts plus replica recovery.
10. Toggle a node offline and upload/download again to explain fault tolerance.
