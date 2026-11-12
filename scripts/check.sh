#!/usr/bin/env sh
set -eu
(cd backend && go test -race ./... && go vet ./...)
(cd frontend && npm run build && npm test && npm audit --audit-level=high)
docker compose run --rm --no-deps engine python -m pytest -q -p no:cacheprovider
python3 scripts/integration.py
python3 scripts/security-check.py
(cd frontend && npm run test:e2e)
