# HeySow isolated verification — 2026-11-06

Development checks use disposable databases, fixture sessions and bounded mock providers. Sending, acquisition and inbox sync are disabled. Dummy JWTs test real local session handling; they do not bypass production authentication. No production deployment, schema change, data cleanup or real email was performed.

## Completed stage-27 evidence

| Gate | Actual result | Persistent evidence |
|---|---|---|
| Complete backend, including PostgreSQL | 599 passed, zero failures/errors, one explicit live-mail skip | backend.log and backend.xml |
| PostgreSQL subset included above | 20 passed, zero skipped | Same full-run JUnit; private local PostgreSQL 16.15 |
| Frontend unit suite | 76 passed | frontend-unit.log |
| TypeScript | PASS | typecheck.log |
| Production frontend build with fixture values | PASS | build.log |
| Existing workflow browser suite | 26 passed | workflows-final.log |
| Auth browser suite | 3 passed | auth.log |
| Gated workspace browser suite | 8 passed | workspaces.log |

Logs above are under data/artifacts/verification/stage27. The exact machine-readable state is in HEYSOW_STABILIZATION_TEST_RESULTS.json. A signed-preview browser test separately checks literal-dollar fixture secrets, zero inherited memberships, explicit creation and onboarding denial in APP_ENV=development, using actual BFF signatures rather than test-mode authentication.

Workspace browser coverage includes selection, stale membership denial, company profile conflicts, invitation create/revoke/accept/replay, personal profile isolation, explicit workspace creation, ICP versions/comparison/duplication and resumable manual setup. Company website, DNS and AI provider tests use synthetic evidence, not the owner's production domain or live provider account.

## PostgreSQL recovery and concurrency

The local server was built from SHA-256-verified official PostgreSQL 16.15 source. It listens only on a private Unix socket. No root production DATABASE_URL is used. Every test creates and drops only its random disposable schema. The original 14 repository/queue/schedule/source/cache/migration checks now use verified membership scopes and current request contracts.

Six additional cases exercise independent connections: duplicate workspace creation, concurrent self-demotion/last-owner preservation, single-use invitation acceptance, optimistic ICP revisions, atomic DNS-check reservations and a real schema-22 pg_dump/psql restore into another random schema. Restored contact history, memberships, settings and onboarding are checked before and after upgrading to 26.

The first PostgreSQL concurrency run found a real users.id/users.email insertion race. The fix handles both conflicts and rechecks the exact ID/email pair; it never adopts an inconsistent identity. Two SQLite integrity tests cover that refusal. A prior combined run exposed Redis leakage in a signature-test fixture that deliberately changes APP_ENV. Redis is now blanked in the offline harness and explicitly isolated in that fixture. The clean complete result above follows that correction. Mock cache tests continue to exercise caching behavior.

## Retained failure evidence and boundaries

An earlier browser run had a context-teardown timeout; its isolated retry passed. Another concurrent auth/workflow run collided in Playwright's shared trace output directory. Per-config artifact directories fixed the harness; the clean workflow run passed all 26. These were not silently counted as passes.

The single remaining skipped test requires separately authorized controlled live Gmail queue acceptance. A skip is not production acceptance. Public registration, customer mailbox/CRM connections, the full discovery-connected customer journey, usage/entitlements, API/MCP and Agent remain incomplete. The local cryptography 48.0.1 versus locked 50.0.2 exception remains a release blocker. Local PostgreSQL does not substitute for approved staging or the owner's final acceptance.

## Repeatable checks

Use the project Python 3.12 .venv with APP_ENV=test and explicit disabled send/sync/acquisition flags. Keep Redis/provider credentials blank in the test process. Enable RUN_POSTGRES_TESTS=1 only with an explicit disposable test URL and official pg_dump/psql tools; never substitute the production URL. Run pytest tests with JUnit output and preserve failures.

From dashboard, npm test, npm run typecheck and a fixture-environment production build are the UI gates. Browser configs are playwright.config.ts, playwright.auth.config.ts, playwright.workspace.config.ts and playwright.preview.config.ts. Shared-port configs run sequentially. Auth has a separate port, build directory and artifact directory. Only gated fixture configs enable workspace management; production flags remain unchanged.


## Subsequent customer-connection checkpoint (schema 27)

The new complete backend result is **610 passed, zero failures/errors, one live-mail
skip**, including **22 PostgreSQL cases**. UI units pass **81**; type checking and
the production build pass. A new browser check passes through the real scoped
authorization endpoint and intercepts Google before any live consent or exchange.
Evidence is `integrations-full.log/xml`, `integrations-frontend-unit.log`,
`integrations-typecheck-final.log`, `integrations-build.log` and
`customer-integrations-browser.log` under the same persistent verification folder.
The preceding 26/8/3/1 browser runs are the frozen schema-26 UI baseline.

The owner's subsequent PlaneByte UI/onboarding/settings/navigation brief is now
being applied. Its changes require their own browser and accessibility acceptance;
these prior results must not be represented as validation of that unfinished UI.
