# Database

PostgreSQL 17 with pgvector. `backend/migrations/001_init.sql` is the idempotent initial schema, applied at startup. Future schema changes should use versioned migrations with an explicit migration ledger before rolling multi-instance deployment.

| Tables | Responsibility |
|---|---|
| users, sessions | bcrypt password hashes; SHA-256 hashed random session tokens with expiry |
| projects, project_members | Project ownership; membership table reserved for future sharing, not exposed |
| project_files | Generated storage keys, content hashes, category, processing state, decoder options and structured analysis |
| documents, document_chunks | Extracted pages/chunks with 384-dimensional semantic vectors |
| investigations, investigation_evidence | Problem/state/resolution and attached evidence links |
| diagnostic_hypotheses, diagnostic_tests | Rule-key-stable hypotheses, structured citations and user-recorded outcomes |
| investigation_events | Append-only diagnostic snapshots, state changes and test observations |
| measurement_files, measurement_results | Waveform metadata and successive analysis results |
| components | Extracted component properties, references and file provenance |
| knowledge_entries | Private project-linked report snapshots and semantic embeddings |
| background_jobs | Durable queue state, attempt counter, errors and recovery timestamps |

All IDs are generated UUIDv4. Foreign keys cascade where records cannot exist without their parent. Owner/project lookups, session expiry, queue state and document joins are indexed. Initial vector search is exact cosine distance, appropriate for bounded projects; add and evaluate approximate indexes only when corpus size justifies them. Large source binaries remain in the upload volume.

Authorization is enforced in the API, including file, investigation and hypothesis relationships. PostgreSQL row-level security is not enabled; do not expose database credentials or direct query access to clients. The `project_members` table does not grant access in this release.

## Backup and restore

Back up the PostgreSQL database and upload volume together. Database rows without the corresponding upload files cannot be reprocessed. Model files live in the engine image; preserve its digest and dependency lock for reproducibility. Exercise restore in an isolated environment before relying on backups. Do not use `docker compose down -v` unless intentionally destroying all local data.

## Embedding compatibility

The deployment uses `BAAI/bge-small-en-v1.5` (384 dimensions). Changing models or switching lexical/semantic modes requires reprocessing documents and regenerating knowledge embeddings. Never rank vectors from different models together.
