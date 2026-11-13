# BenchTrace execution status

No production-completeness claim is made until all required checks pass.

| Stage | Status | Acceptance |
|---|---|---|
| 0 Repository inspection | Complete | Empty repository; Go, Python, Node, Docker and GitHub available |
| 1 Foundation | Implemented; regression verification underway | Sessions, owner isolation, projects, versioned migrations, React workspace |
| 2 Documents | Implemented supported subset | PDF/text extraction, structured explicit characteristics, local semantic retrieval, cited answers |
| 3 Signals | Implemented supported subset | Validated CSV, numerical analysis, bounded I2C/UART/SPI, waveform controls and comparison |
| 4 Engineering intelligence | Supported subset implemented | Bounded Arduino/ESP-IDF firmware patterns; KiCad `.net` connectivity and bounded root-sheet orthogonal `.kicad_sch` topology; unsupported geometry and broader AST/control-flow analysis are documented |
| 5 Diagnostics | Implemented I2C workflow | Selected evidence, problem scope, five competing rule families, traceable tests and ranking |
| 6 Product workflow | Implemented and browser verified | Durable investigations, reports, procedures/components/knowledge, scoped WebSocket events and browser regression |
| 7 Production quality | Ongoing audit | Security checks and source/published-image local deployments pass; full workflow 43390628067 passes; remaining audit boundaries are recorded in docs/REQUIREMENTS.md |
| 8 Release | Release candidates published | Required docs, screenshots, reproducible simulation, milestone pushes and GHCR images for all three services; no stable release or hosted production deployment claimed |

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

Extended `.kicad_sch` extraction to read embedded library symbol pin numbers, names, and declared electrical pin types for recognized component symbols. This metadata is explicitly not treated as net connectivity; exported `.net` remains the source for reliable pin-to-net relationships. Added a simulated sensor-symbol fixture and wired it into API and browser workflows to verify stored pin metadata through both evidence and component views. A stronger upload test exposed malformed fixture structure (first an unclosed expression, then a misplaced close that nested the component under library definitions); the fixture is corrected and the end-to-end API and browser checks pass. Verification: engine suite **63 passed** (one upstream Starlette/httpx deprecation warning); rebuilt engine/API integration and security integration passed; browser suite **4 passed**. Full CI run **43380716786 passed** for the code revision before the fixture correction; CI for the corrected fixture is pending. A direct host Python test attempt failed during collection because the host interpreter lacks the engine package; passing tests used the pinned Compose engine environment.

## Milestone 8 — visible KiCad pin evidence

Added declared pin metadata to both the uploaded schematic evidence view and the project component browser. The views distinguish symbol pin metadata from net connectivity, and the component browser scrolls its wide table within the panel on mobile so columns remain readable. Expanded the complete browser workflow to upload the simulated KiCad symbol file, verify extracted pin evidence, and browse the same component at project scope. Verification: frontend build and **2 unit tests passed**; browser suite **4 passed**. An earlier run exposed a stale toast assertion and mobile table overflow; the test flow and layout are corrected. The tests also refreshed desktop and mobile screenshots. Full CI run **43378902991 passed** for the pin view and mobile-scrolling revision.

## Milestone 9 — waveform extrema visibility

Signal statistics now count local maxima and minima using the same 10%-of-peak-to-peak prominence threshold, label the method, and display both counts in the waveform workspace. Added an engine assertion for a known 1 kHz, 100-cycle signal and an end-to-end browser assertion for both channels. Verification: engine suite **59 passed** (one upstream deprecation warning); frontend build and **2 unit tests passed**; browser suite **4 passed**. A first browser attempt exposed an ambiguous selector because two channels correctly render the same metric label; it now asserts both rows. Full CI run **43379575721 passed**.

## Milestone 10 — ESP-IDF I2C configuration extraction

Extended bounded firmware analysis to recognize `i2c_master_bus_config_t` SDA/SCL designated fields and `i2c_device_config_t` address/clock fields, including `GPIO_NUM_N` pins and project macro aliases that resolve to numeric constants. The extracted bus pins now feed existing schematic-to-firmware consistency checks. Device address width is retained: a configured 10-bit address is not flagged as an invalid 7-bit value or compared to 7-bit datasheet excerpts. Analysis remains static and does not follow handles or establish that initialization executes. Verification: engine suite **63 passed** (one upstream deprecation warning); rebuilt API integration and security integration passed. The first focused run had one test assertion mismatch in expected wording; corrected and rerun. Full CI run **43380716786 passed** for the alias and width-aware evaluation revision. The corrected KiCad fixture then passed the complete CI workflow **43381477197**, including engine tests, API/security integration and browser upload/pin rendering.


## Milestone 11 — corrected KiCad upload demo

Clarified the reproducible workflow to upload the `.kicad_sch` symbol fixture separately, then rely on the exported `.net` for assumed pin-to-net connectivity. This avoids implying the schematic symbol parser reconstructs wires. Full CI run **43381477197 passed** for the corrected fixture and API/browser coverage; follow-up documentation runs **43381658413** and **43382157097** also passed.


## Milestone 12 — release image verification

Verified public GHCR manifests for backend, frontend and AI engine at `v0.1.0-rc.1`; pulled the AI engine image and confirmed its registry digest (`sha256:53e68d1e851ac903e6eea98ea1b64b587e7d53875640aab924e6ea1b829359a6`). This confirms registry availability and image retrieval, not a hosted production deployment.


## Milestone 13 — final audit CI pass

The complete workflow passed on commit `404018e` as run **43382157097**: Go race tests and vet, frontend production build/unit tests/audit, container build, 63 engine tests, API and security integration, and Playwright browser regression. The workflow emits only upstream GitHub Action/runner deprecation notices. Local Compose services are healthy.


## Milestone 14 — bounded KiCad schematic topology

The `.kicad_sch` parser now derives root-sheet nets from orthogonal wire segments, symbol pin coordinates, labels, explicit junctions and power-symbol values for unmirrored symbols at right-angle rotations. Unmarked interior crossings remain separate; unsupported buses, hierarchy, mirrored symbols, diagonal wires and non-right-angle transforms are disclosed. Topology operation limits discard the derived graph rather than returning a partial result. The demo sensor schematic now connects all four pins to local labels, while `circuit.net` continues to provide assumed full-project connectivity.

Verification against the pinned engine image: **67 engine tests passed** (one upstream Starlette/httpx deprecation warning), including separate crossing, junction, rotated-pin and topology-budget fixtures. The parser also extracted six components and eleven pin connections across four nets from [KiCad's published rectifier schematic](https://github.com/KiCad/kicad-source-mirror/blob/master/demos/simulation/rectifier/rectifier.kicad_sch). Rebuilt local API integration and negative security checks passed; Playwright **4 passed**, including selecting `SDA` and seeing U3 pin 1. Frontend unit tests **2 passed**. Full CI run **43387281908** passed for feature commit `1f6e865`, including engine, API/security, frontend and browser jobs.


## Milestone 15 — schematic topology CI

The GitHub Actions workflow **43387281908** passed on `1f6e865`: Go race/vet, frontend build/unit tests/audit, Docker build, 67 engine tests, API and security integration, and all four Playwright tests. Only upstream action/runner deprecation annotations were emitted.


## Milestone 16 — versioned prerelease images

Created and pushed annotated tag `v0.1.1-rc.1`. GHCR publication workflow **43387718543** passed for backend, AI engine and frontend. All three public manifests resolve, and the updated AI engine image was pulled and exercised against the demo schematic, returning four sensor pin-to-label nets. Engine digest: `sha256:1b074013dd2d13a9e9316b2c919c8926a463232fe3ddb67dd36fd3af49c3b77c`. Final audit-doc CI run **43387690703** passed for commit `20b03b2`. This is a release candidate, not a production-completeness claim or hosted deployment.


## Milestone 17 — schematic source attribution in diagnosis

Corrected the pin-consistency hypothesis to cite extracted circuit evidence by source filename instead of labeling every circuit as an exported netlist. Added a fixed evaluation that builds SDA/SCL nets from `.kicad_sch` label/pin geometry, ranks a firmware pin mismatch as supporting evidence, and treats matching firmware pins as contradictory evidence. The verification test recommendation now refers to extracted schematic or netlist connections. Verification: **68 engine tests passed**; rebuilt API integration and security integration passed; Playwright **4 passed**. Full CI run **43388763329** passed on source commit `67cbaf1`.


## Milestone 18 — source-attribution CI

Full workflow **43388763329** passed on `67cbaf1`: Go race/vet, frontend build/unit tests/audit, Docker build, all 68 engine tests, API/security integration, and four Playwright tests. Only upstream GitHub Action/runner deprecation notices were emitted.


## Milestone 19 — deployment from published images

Added `compose.published.yaml` to replace local `build` entries with versioned GHCR images while reusing the same health checks, networks, storage, secrets and resource limits. Added `BENCHTRACE_PORT` so isolated deployments can use a separate loopback port. Compose config validation confirms all three services resolve to `v0.1.2-rc.1` images with no build contexts.

Pulled all services and dependencies, started an isolated published-image stack on port 8081, and verified API health, API integration, negative security integration, and all **4 Playwright tests** against those published containers. The stack was stopped and its test volumes removed. This verifies local deployment from registry images; it is not public cloud hosting. Full CI run **43390628067** passed on the Compose overlay commit, including Go race/vet, frontend build/unit/audit, engine tests, API/security integration and all four Playwright tests. The CI job also validates that the published overlay resolves three GHCR images without build contexts.
