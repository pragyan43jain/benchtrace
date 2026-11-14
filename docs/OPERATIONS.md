# Local backup, recovery and monitoring

Run `python3 scripts/backup.py` from any directory. This creates a private directory in `.data/backups/`, briefly stops web/API/engine writers, exports PostgreSQL and uploads, writes SHA-256 checksums, then restarts previously running application services even on failure. Schedule during a maintenance window. Do not run concurrent backups, deployments or direct database writers. A backup without its final manifest is incomplete. Redis caches and rate-limit counters are intentionally not restored; durable jobs live in PostgreSQL.

Back up `.env` separately in an encrypted secret store. In particular, the original provider encryption key is required to read saved account keys. Backup contents include private engineering files, password hashes and sessions: protect them as production data. Checksums detect accidental corruption, not a malicious replacement of both payload and manifest. Only restore trusted backups.

Restore into a new isolated deployment:

```sh
python3 scripts/restore.py .data/backups/TIMESTAMP benchtrace-restore-check 8091
```

The script verifies checksums and rejects archive links/traversal. It refuses existing project resources, builds current source images, and restores into fresh named volumes using the current `.env`. Keep the matching source revision with each backup; newer schema migrations may prevent rollback. Failed restores leave the isolated project for inspection; remove that project explicitly before retrying. Never remove the original deployment volumes.

Validate restored records, upload contents and account access before switching users to a restored deployment. Use the same project name, `BENCHTRACE_PORT` and `APP_ORIGIN` on subsequent Compose commands. Restoring is not an automatic replacement of the original deployment.

`GET /api/live` checks API process liveness. `GET /api/health` checks PostgreSQL, Redis and the engine concurrently with a three-second deadline and returns 503 on dependency failure. It does not certify queue throughput or model correctness. `python3 scripts/monitor.py` exits nonzero for degraded readiness and can be called by an external scheduler/alert service. No alert destination or backup retention policy is configured automatically.
