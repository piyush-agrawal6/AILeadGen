# Phase 3 audit and implementation log

Date: 2026-10-25. Existing Phase 1/2 implementation and uncommitted changes are preserved.

## Baseline

- Python 3.12.10: 31 passed, one Starlette/httpx deprecation warning (34.07 seconds).
- Node 24.19.0; npm 11.17.0.
- Doctor: Python, SQLite migrations, DuckDB, Chrome, Lighthouse, Playwright and Overture ready; Overpass warning.
- First npm ci attempt failed with EPERM because the existing Next development server held the SWC binary. Stopped only the repository's Next server and retried.
- Frontend checks attempted while retry installation was incomplete could not find package executables; these are not test failures and must be rerun after installation.
- Full frontend baseline reproduced after installation: TypeScript zero errors, lint zero errors, 8 tests passing, Next 14.2.35 production build successful (10 application pages plus generated not-found route). Baseline install: 578 packages in six minutes.
- Baseline npm audit: 15 vulnerabilities (3 critical, 6 high, 6 moderate). Reports saved before upgrades.
- Python audit initially found 12 advisory entries against pip 25.0.1 only; upgrading pip to 26.2.2 yielded no known vulnerabilities.
- Fetch hardening preserves all 31 original tests. Added 11 security tests passing.

## Audit findings

- Next 14 unsupported. Official support policy lists Next 16 Active LTS.
- Registry latest stable Next 16 version observed: 16.4.3.
- Auth.js official Next App Router implementation is next-auth 5 beta (registry beta.32); v4 remains maintenance. Any beta use must be pinned and documented as a specific exception to satisfy current official App Router integration guidance.
- Existing probe/crawler disable TLS certificate verification and auto-follow redirects before checking targets. Must replace with bounded fetching, per-hop DNS/IP checks, TLS verification, robots handling.
- SQLite repository uses parameterized SQL and ON CONFLICT; a small DB-API adapter can retain repositories with PostgreSQL support. INTEGER autoincrement/row IDs and SQLite date functions need explicit portability handling and real integration tests.
- API currently unauthenticated, frontend uses public backend env/rewrite. Replace with authenticated server BFF and signed API requests, persistent replay protection.
- Production startup currently migrates automatically. Production must require explicit versioned migration.
- Pipeline resume currently rediscovers and reinserts observations. Requires idempotency before cloud retries.
- Exports currently local files with date-only names; cloud artifacts need stable run keys.
- Existing settings updates are process-local. Shared hosted settings must persist.

## Infrastructure preflight (read-only)

- Configured GCP project querryside (248535449008), region asia-south1, ACTIVE, billing enabled.
- Cloud Run, Artifact Registry, Cloud Build, Secret Manager and Cloud Quotas APIs enabled.
- No Cloud Run jobs in configured region at initial inspection.
- gcloud authenticated; Vercel CLI authenticated. Docker CLI installed but Linux daemon unavailable.
- Database, OAuth, API-signing, R2 and GCP configuration keys present; secret values not logged.
- ALLOWED_USER_EMAILS was absent. User supplied planebyte@gmail.com and subsequently explicitly requested only this account.
- Actual PostgreSQL connectivity succeeds (server 18.6, zero public tables initially); R2 HeadBucket succeeds.
- Quota data retrieved with gcloud quotas info list; the older beta services quota command is unavailable. Regional CPU/memory/task values still require filtered recording.

## Official references

- https://nextjs.org/support-policy
- https://nextjs.org/docs/app/guides/upgrading/version-16
- https://nextjs.org/docs/app/api-reference/file-conventions/proxy
- https://authjs.dev/getting-started/integrations
- https://authjs.dev/getting-started/migrating-to-v5

## Additional security verification

The fetch transport now pins validated public DNS addresses for TCP connections while retaining the original TLS hostname/SNI. All 12 HTTP security tests pass, including a rebinding regression. Public transport/network backend APIs follow https://www.python-httpx.org/advanced/transports/ and https://www.encode.io/httpcore/network-backends/.

## Final local validation

109 Python tests pass, including real PostgreSQL integration, session-lock and canary evidence checks. The dashboard passes strict TypeScript, ESLint, 26 Vitest tests and the Next.js 16 production build. The three deterministic Playwright acceptance tests pass. Frontend and Lighthouse npm audits and the Python package audit report zero known vulnerabilities. TypeScript 6.0.3 was selected because the newer TypeScript 7 registry release was outside the supported typescript-eslint range. The dependency lockfiles record the exact installed versions.
