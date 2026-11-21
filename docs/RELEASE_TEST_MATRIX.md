# Reproducing the production release checks

Use a clean, disposable checkout of the release SHA, without operator `.env` files. Use Python 3.12, Node 24, `requirements.lock`, `dashboard/package-lock.json`, and the Chromium revision installed by Playwright. Use a dedicated **local** PostgreSQL 18 database and the matching client bin directory; the restore test runs `pg_dump` and `psql` as separate processes. Never point these checks at a customer database.

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
# Set DATABASE_URL to the disposable local DB and HEYSOW_PG_TEST_BIN to its PG18 clients.
APP_ENV=test RUN_POSTGRES_TESTS=1 .venv/bin/python -m pytest -q
(cd dashboard && npm ci && npm run typecheck && npm run lint && npm test && npx playwright install --with-deps chromium)
bash scripts/verify_browser_matrix.sh
```

The browser command checks the source tree and (on Actions) `GITHUB_SHA`, compiles into a new Next build directory, logs its build ID, then runs all six suites sequentially on ports 13000/18787. Run from a fresh checkout when repeating: Next can update generated type references during compilation. The backend and frontend restart with suite-specific settings each time. Startup readiness checks and original action/test timeouts remain enabled. Failures are aggregated; one failed suite does not prevent the others from reporting.

| Suite | Coverage | Startup and data |
|---|---|---|
| Legacy workflow (29) | Session/CSP, campaigns, acquisition review, signed proxy limits, operations, prospecting, schedules, archived feature denial | Plain Uvicorn `app.api.server:app` + `next start`. Disposable SQLite, Lead Engine available for these tests. Includes real local API requests and explicitly intercepted provider responses. |
| Release journeys (17) | Accounts (1), workspace (11), subscription (1), onboarding (2), Radar destinations (2) | Suite-specific Uvicorn fixture apps with seeded roles, entitlements, onboarding, or provider inputs; same built Next app via `local_frontend.cjs start`. Each has a new SQLite path. Workspace explicitly enables the legacy product; billing/intent-only fixtures keep it off. |

SQLite validates browser behavior; it does **not** certify deployed PostgreSQL compatibility. Hosted pytest separately exercises the clean Radar migration chain, checksums, structural drift and restore behavior on PostgreSQL 18. A fresh production dump restored and upgraded on an isolated server is a separate promotion gate. The `production-source` job independently checks ancestry and packages the exact SHA, including a deliberately invalid metadata control. Record all gates for the same commit before deploying.

On failure, the Actions log identifies the suite and request/assertion. Download the restricted `browser-diagnostics` artifact and inspect `trace.zip`, screenshots and `error-context.md` for that SHA and suite. Traces can contain fixture session cookies; do not publish raw traces or headers.
