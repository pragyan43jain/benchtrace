# Contributing

Start with a reproducible hardware failure, supported evidence, and a test that can falsify the proposed explanation. Keep contributions focused on engineering investigations.

1. Open the engineering workflow proposal template for new capabilities or the defect template for reproducible failures. Label all simulated captures and remove secrets and proprietary inputs.
2. Fork and branch from main. Keep secrets and proprietary hardware files out of commits.
3. Run the checks below and explain any unavailable infrastructure.
4. Submit a PR describing the failure before/after, evidence provenance, test results and limits.

```sh
(cd backend && go test ./... && go vet ./...)
(cd frontend && npm ci && npm run build && npm test)
python3 scripts/setup-env.py
docker compose build
docker compose up -d
docker compose run --rm --no-deps engine python -m pytest -q -p no:cacheprovider
python3 scripts/integration.py
(cd frontend && npx playwright install chromium && npm run test:e2e)
```

For local system Chrome, set `CHROME_PATH=/usr/bin/google-chrome` for browser tests. Unit signal fixtures must include known outputs, invalid inputs and sampling-limit cases. Diagnostics must cite existing evidence, express contradictions and offer a confirm/reject experiment. Do not add uncalibrated confidence percentages or hardcoded dashboard data.

Code ownership: Go manages app state and access; Python performs extraction and engineering computation; React displays actual API data. Prefer bounded parsers and deterministic checks before adding probabilistic interpretation. New schemas require constraints, indexes and migration notes. Document every unsupported input mode visibly.
