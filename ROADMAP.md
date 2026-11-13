# BenchTrace execution status

No production-completeness claim is made until all required checks pass.

| Stage | Status | Acceptance |
|---|---|---|
| 0 Repository inspection | Complete | Empty repository; Go, Python, Node, Docker and GitHub available |
| 1 Foundation | Implemented; regression verification underway | Sessions, owner isolation, projects, versioned migrations, React workspace |
| 2 Documents | Implemented supported subset | PDF/text extraction, structured explicit characteristics, local semantic retrieval, cited answers |
| 3 Signals | Implemented supported subset | Validated CSV, numerical analysis, bounded I2C/UART/SPI, waveform controls and comparison |
| 4 Engineering intelligence | Partially implemented | Bounded firmware patterns, KiCad netlist graph, visible schematic pin metadata; broader static-analysis and schematic geometry remain |
| 5 Diagnostics | Implemented I2C workflow | Selected evidence, problem scope, five competing rule families, traceable tests and ranking |
| 6 Product workflow | Implemented; browser regression underway | Durable investigations, reports, procedures/components/knowledge, scoped WebSocket events |
| 7 Production quality | In progress | Security checks and local deployment pass; full CI run 43376992920 passes; product audit items remain |
| 8 Release | In progress | Required docs, screenshots, reproducible simulation and GitHub milestones; GHCR prerelease workflow 43374242750 succeeded for all three images |

## Design commitments
- All demo captures explicitly simulated; no physical verification claims.
- Evidence links and transparent rules precede optional LLM explanation.
- No arbitrary probabilities. Ranking reflects rule matches and contradictions.
- Owner-only projects initially; no unimplemented sharing implied.
- Unsupported formats and ambiguous captures fail visibly.

## Milestone 1 — implemented foundation and engineering core

Created `backend/` (schema, sessions, ownership, storage, durable jobs, investigation/report APIs), `ai-engine/` (signal algorithms, bounded firmware/KiCad/document extraction, evidence ranking), `frontend/` (React workspace and uPlot viewer), `compose.yaml`, and reproducible `demo/` fixtures.

Executed: `go test ./...` passed for auth/storage; initial Python suite **18 passed** after correcting I2C STOP-boundary handling. Frontend initial build caught an unavailable icon export (fixed); npm audit found old tooling vulnerabilities (upgrades underway).

Remaining verification: full container startup, API integration, browser workflows, semantic model download and retrieval evaluation, dependency/security audits, deployment and CI. No completion claim for unverified endpoints.

## Milestone 2 — integrated local investigation

Added semantic BGE/pgvector retrieval, constrained extractive RAG, configurable protocol decoding, waveform comparison, circuit net visualization, profile/password updates, knowledge retrieval, CI definitions, integration/browser tests and required documentation.

Executed against the running Compose stack: **API integration passed** for registration/login/logout, CSRF rejection, project management, second-account isolation, ZIP ingestion, background processing, waveform decoding, document retrieval, diagnosis, persisted test outcomes across reruns, report generation and private knowledge storage. Engine evaluation: **30 passed** before the additional circuit-correlation test. Frontend: production build and **2 unit tests passed**. npm audit: **0 vulnerabilities**.

Open gates: browser E2E, final rebuilt images, Go/Python dependency remediation and rescan, GitHub CI execution, final documentation/screenshots. Earlier Go/Python audits detected vulnerable initial pins; upgrades are in progress. Public hosting and physical hardware validation are not claimed.


## Milestone 3 — audit-driven completion work

Created `docs/REQUIREMENTS.md` to preserve the full requested scope. Added structured source-backed datasheet characteristics, disposable parser processes with CPU/memory/wall-time limits, checksum-verified database migrations, project history/defaults, selected investigation evidence, standalone procedures, component browsing, verified-result filtering, source-hash report manifests, storage quotas and atomic Redis API rate limits. Split evidence, hypothesis and knowledge UI modules; waveform tools are loaded on demand. Added provider-contract, parser, API and browser isolation coverage. Completed the README with real screenshots and startup instructions.

Executed against the rebuilt stack: expanded API integration **passed**, including PDF upload, preferences, selected evidence, components/history, waveform comparison, procedures, verified filtering and account updates. Negative security integration **passed**. Engine suite **48 passed** against source (image regression is running). Frontend production build and **2 unit tests passed**; npm audit **0 vulnerabilities**. Prior Go and Python package scans were clean after remediation; current Go rescan and three browser scenarios are running.

Remaining: exercise release-image publication and close the remaining audit rows. No claim of 100% completion or public production hosting.

Milestone 3 verification completed: rebuilt-image engine suite **48 passed** (one test-client deprecation warning); browser suite **3 passed** (full investigation, session restore/login/logout, owner-only WebSocket events); Go race tests and vet **passed**; `govulncheck` **no vulnerabilities found**. Both API integration suites passed on the rebuilt stack. Remaining work is tracked in the requirement audit; a green final CI and exercised release workflow are still required.

## Milestone 4 — pinned retrieval and verification

Pinned the semantic model to an immutable repository revision and verified every downloaded artifact with SHA-256 during image builds. Added vector identity to document and knowledge records, version-scoped cache/search behavior, and bounded idle-worker migration of legacy vectors from preserved source text. Firmware analysis now resolves common numeric constants and flags same-pin I2C setup and invalid seven-bit targets with contextual explanations. Added UART/SPI capture-boundary uncertainty reporting and automated WCAG scans.

Verified: engine suite **56 passed**; API integration and negative security workflows passed; browser suite **4 passed**, including desktop/mobile WCAG scans; Go race tests/vet passed; GitHub Actions run **43373860041 succeeded** across Go, frontend, Docker, engine, API/security and browser jobs. Local database migration 003 applied and all 35 existing vectors carry the pinned model identity. GHCR image publication was verified by workflow 43374242750; no hosted production deployment is claimed.


## Milestone 5 — expanded I2C diagnostic evaluation

Added fixed scenarios for chained address constants, strap-dependent alternate addresses and invalid 8-bit values passed to the 7-bit Wire API. The engine suite now reports **56 passed**. Commits `e3150bc` (unchecked I2C read finding) and `dad82b7` (expanded dataset) are pushed; their CI runs are green. GHCR prerelease workflow `43374242750` completed successfully for backend, engine and frontend. Pulling the large engine image locally remains unverified; the backend image pull succeeded.


## Milestone 6 — verification feedback in the investigation UI

Recording a user test now immediately reruns the diagnosis using the selected evidence and saved test observations, then reloads hypothesis ranking and status. The UI displays the ranking method and identifies test observations as user-recorded evidence. Local production build and Vitest pass; focused Playwright investigation regression passes against the rebuilt web container. The first UI commit CI run 43375259585 failed because its E2E selector used the old disclosure label. The updated test and UI passed full browser CI in run 43375475924. The full master audit remains open.

## Milestone 7 — KiCad symbol pin metadata

Extended `.kicad_sch` extraction to read embedded library symbol pin numbers, names, and declared electrical pin types for recognized component symbols. This metadata is explicitly not treated as net connectivity; exported `.net` remains the source for reliable pin-to-net relationships. Added the simulated sensor-symbol fixture and wired it into the API integration suite, which now verifies stored pin metadata through the component endpoint. Verification: engine suite **59 passed** (one upstream Starlette/httpx deprecation warning); rebuilt engine/API integration and security integration both passed. Full CI run **43376992920 passed** across Go, frontend, engine, API/security, and browser workflows. Local browser suite **4 passed** and refreshed the workspace screenshots. Earlier run 43376592983 exposed one stale scope-wording assertion; the test was corrected and the subsequent full run is green. A direct host Python test attempt failed during collection because the host interpreter lacks the engine package; passing tests used the pinned Compose engine environment.

## Milestone 8 — visible KiCad pin evidence

Added declared pin metadata to both the uploaded schematic evidence view and the project component browser. The views distinguish symbol pin metadata from net connectivity, and the component browser scrolls its wide table within the panel on mobile so columns remain readable. Expanded the complete browser workflow to upload the simulated KiCad symbol file, verify extracted pin evidence, and browse the same component at project scope. Verification: frontend build and **2 unit tests passed**; browser suite **4 passed**. An earlier run exposed a stale toast assertion and mobile table overflow; the test flow and layout are corrected. The tests also refreshed desktop and mobile screenshots. CI for this milestone is pending.
