# Security policy and deployment boundaries

Report vulnerabilities through GitHub private vulnerability reporting when enabled, or contact the maintainer privately. Do not post secrets, proprietary firmware, or exploit payloads in public issues.

Implemented protections:

- bcrypt cost 12; 256-bit random session tokens stored only as hashes; seven-day expiry; HttpOnly, SameSite=Strict cookies; configurable Secure flag.
- Exact Origin validation on mutations and authenticated project ownership on every data route.
- Parameterized SQL, bounded JSON/multipart bodies, UTF-8/content validation and UUID storage paths.
- ZIP entry count, expanded-size, traversal, symlink and duplicate-name checks. Uploaded firmware is never executed.
- Internal engine bearer authentication; read-only source volume and engine root filesystem; container CPU/memory limits.
- Atomic Redis-backed rate limits (20 authentication mutations/minute, 3 provider connection checks/minute per authenticated account, and 600 other API requests/minute per proxy peer) fail closed when Redis is unavailable. File storage is limited to 200 files/project and 1 GiB/account.
- Browser CSP, no raw HTML rendering of uploaded text, restrictive framing and content-sniffing headers.
- Optional LLM only selects existing citation IDs. It cannot supply source text, measured values or confidence scores. Provider secrets remain server-side.
- The authenticated provider connection check submits only a fixed synthetic citation marker, never uploaded engineering evidence. It returns a generic result without forwarding provider response bodies or credentials.

## Before public deployment

Set `APP_ORIGIN` to the exact HTTPS origin and `COOKIE_SECURE=true`. Place nginx behind a trusted TLS reverse proxy. Keep PostgreSQL, Redis and the engine on a private network. Store `.env` securely and rotate secrets if exposed. Configure backups, restore testing, disk quotas, alerting, dependency updates and external review appropriate to the sensitivity of uploaded engineering IP.

The default Compose service binds web access to loopback. This is a local deployment, not an internet-facing multi-tenant service. The authentication limiter sees the internal proxy address and therefore conservatively shares its limit; trusted per-client proxy handling is a future deployment hardening task.

Known limitations are tracked in ROADMAP.md. Document parsing runs in a disposable process without provider/service credentials, with 65-second wall time, 60-second CPU, 2 GiB address-space and output/file limits, inside the resource-limited container. This is a parser isolation measure, not a VM or a security guarantee against every native-library exploit. No antivirus, OCR, email verification, recovery email, MFA or organization sharing is claimed. Uploaded source content may contain malicious instructions; even correctly cited documentation can be false or inapplicable. User-recorded confirmation is not independent physical verification.

Electrical tests should be limited to isolated low-voltage bench setups and qualified operators. BenchTrace cannot assess the safety of an unknown physical circuit and is not a safety certification tool.
