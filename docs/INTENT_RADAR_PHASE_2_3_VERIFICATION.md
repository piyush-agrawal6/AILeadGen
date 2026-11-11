# Intent Radar Phase 2/3 final verification and recovery report

## Current independent product-audit baseline — 2026-11-11

Prior evidence below is preserved and checkpointed. It is superseded for current
full-product completion by `INTENT_RADAR_PHASE_2_3_COMPLETE_FUNCTIONAL_AUDIT.md`,
`INTENT_RADAR_PHASE_2_3_UI_ACCEPTANCE.md` and
`INTENT_RADAR_PHASE_2_3_FINAL_READINESS.md`.

| Current check | Actual result | Additive evidence under `data/artifacts/verification/` |
|---|---|---|
| Backend | 822 passed, 57 skipped; initial 9 harness failures retained | `intent-radar23-product-backend-closure.{log,xml}` |
| Isolated PostgreSQL | 56 passed | `intent-radar23-product-postgres-recovery.{log,xml}` |
| Frontend units | 143 passed | `intent-radar23-product-units-final.log` |
| Supported Node runtime/build | v24.22.2 x64; types and isolated production build pass | `intent-radar23-product-build-routes.log`, `intent-radar23-product-types-closure.log` |
| Browser | 61 distinct scenarios; UI-mocked regressions distinguished from real routing | Product suite JSON/logs and new UI acceptance report |
| Live sources | HN including opt-in jobs; SE, W3C RSS, Discourse Meta; combined three-source check | `intent-radar23-product-live-sources-final.log`, live browser |
| Vertex | Genuine editable draft + selected-ICP interpretation pass | `intent-radar23-product-browser-live-final.log` |
| AI smoke quality | **FAILED 7/8 exact categories**, independent larger set not done | `intent-radar23-product-live-ai-final.log` |
| Full requirements | 355 verified / 505 applicable; 30 missing, 50 partial, 66 unverified | Requirements audit and counts JSON |

Do not sum overlapping reruns or reinterpret historical scope as complete
customer acceptance. Launch remains **NO-GO** for named local software/quality
blockers plus external approvals/staging. No production/mail/credential changes.

### Preserved prior verification report

Date: **2026-11-11**. Base HEAD: `03398f62a3c040e2220157fd7726d7c1233c6969`.
Existing Phase 1/UI/Gmail/B04 and shared-platform edits were retained. The local
Phase 2/3 implementation and acceptance repairs are complete. External gates in
[the pending report](INTENT_RADAR_PHASE_2_3_PENDING.md) prevent a production-readiness claim.

## Final measured baseline

Evidence root: `data/artifacts/verification/`. `intent-radar23-final-baseline.json`
contains current source SHA-256 values, exact XML/browser results and live summaries.

| Check | Actual final result | Evidence |
|---|---|---|
| Full backend | **808 passed, 56 skipped**, zero failures/errors; 307.49 seconds | `intent-radar23-backend-frozen.{log,xml}` |
| Real PostgreSQL regression and P2/3 acceptance | **55 passed, 0 skipped**, zero failures/errors; 71.03 seconds | `intent-radar23-postgres-final.{log,xml}` |
| Combined distinct backend baseline | **863 passed, one live-mail skip**: 55 PostgreSQL skips above were separately executed | Two results above; not a claim of one combined invocation |
| Frontend units | **143 passed**, 37 files | `intent-radar23-frontend-repaired.log` |
| TypeScript | PASS, `tsc --noEmit` | `intent-radar23-types-frozen.log` |
| Production frontend build | PASS, Next 16.4.3 webpack, compilation/types/64 static pages | `intent-radar23-build-final.log` |
| Phase 2/3 fixture browser | **1 passed** | `intent-radar23-browser-final.log` |
| Existing Intent Radar browser | **7 passed** | `intent-radar23-radar-final.log` |
| Lead Engine workflows/campaigns | **29 passed** | `intent-radar23-lead-engine-final.log` |
| B04 Gmail lifecycle/campaign/reply recovery | **2 passed**, synthetic transports, zero real sends | `intent-radar23-gmail-final.log` |
| Genuine public-source/Vertex browser | **1 passed** | `intent-radar23-live-browser-final.log` |
| Shared auth/OAuth handoff | **3 passed**, Google destination intercepted | `intent-radar23-platform-auth-repaired.log` |
| Workspace/ICP/onboarding/isolation browser | **11 distinct passed**: reuse 9 original passes + rerun 2 repaired cases | `intent-radar23-platform-workspace.log`, `intent-radar23-platform-workspace-final.log` |
| Shared customer Sheets handoff | **1 passed** | `intent-radar23-platform-integrations.log` |
| Redesigned UI/responsive browser | **5 distinct passed**: reuse 4 original passes + rerun repaired journey | `intent-radar23-platform-ui.log`, `intent-radar23-platform-ui-repaired.log` |
| Browser total | **60 distinct passing checks**, no unresolved failures | Results above; targeted reruns are not double-counted |
| Genuine sources | Seven successful checks; 94 initial distinct retained signals, four source families | `intent-radar23-live-sources-final.json`; connector matrix |
| Vertex AI quality | Eight cases PASS; zero false-positive labels or negative scores ≥75 | `intent-radar23-ai-quality-{initial,final}.json`; Phase 3 report |

Backend warnings remain seven existing deprecation/JUnit-record-property warnings.
Node 26.13.0 was the actual frontend runtime; supported Node 24 acceptance remains
an explicit gate. Types/build success is not a supported-runtime or deployment claim.

## Execution and isolation

Backend commands used `.venv/bin/python` (Python 3.12.14). Full `pytest -q` ran
after the connector/cache repair. PostgreSQL tests ran with `RUN_POSTGRES_TESTS=1`,
`DATABASE_BACKEND=sqlite` for unrelated fixture sessions and a local-only URL to
the newly created `intent_radar23_acceptance_utf8` database on 127.0.0.1:15443.
Tests allocate unique schemas and independent worker connections. All 43 current
migrations applied; no existing database was reset or overwritten.

Frontend commands were `npm test`, `npm run typecheck`, and
`node ../scripts/local_frontend.cjs build --webpack`, using isolated
`.next-intent-radar23-build` and disposable session/OAuth fixture values.
Playwright configurations were `playwright.intent-radar23.config.ts`,
`playwright.intent-radar23-regression.config.ts` (radar and Lead Engine),
`playwright.intent-radar23-gmail.config.ts`, `playwright.intent-radar23-live.config.ts`
and `playwright.intent-radar23-platform.config.ts` (auth/workspace/integrations/UI).
The live database is restricted to the approved temporary root:
`intent-radar-23-resume-live.db`. The final inspection records zero businesses,
contact people, workflow runs or email messages created by Intent Radar.

Scheduled dispatch, quotas, source revocation, cancellation, monitor revisions,
lease fencing, duplicate workers, retry bounds, workspace isolation, durable
cooldowns and expired-lease recovery pass in the relevant isolated tests.
SQLite backup/restore preserves contact and suppression history. PostgreSQL
worker recovery and migration execution are tested; no production restore claim.

## Failures found, retained and resolved

1. Vitest initially reported 143 unit passes but **three collection failures**
   from Playwright UI files. Corrected the directory exclusion; browser tests ran.
2. Feed configuration edits could reuse stale cache/ETags. Added exact config
   digests and a positive/replacement test; full backend rerun passed.
3. PostgreSQL initial SQL_ASCII database yielded **2 passes, 12 failures, 36 errors**;
   new Radar cases yielded five setup errors. Created a new UTF-8 database, leaving
   the first disposable database intact. No application cast/bypass was introduced.
4. UTF-8 run: **51 passes, two failures, two errors**. Two new acceptance fixtures
   needed independent schema-bound shared-budget sessions and asynchronous worker
   dispatch. Existing customer-connection fixtures needed an explicit allowlisted
   test identity to exercise the authorized flow. Runtime access checks retained.
5. Auth browser: 2 passes/1 locator failure from Next's extra route-announcer alert.
   Scoped assertions to the actual visible auth error and retained safe-text checks;
   all three pass.
6. UI browser: 4 passes/1 outdated preset assertion. Asserted the actual marketing
   recommendation preset; the full subsequent reviewed website-filter workflow
   remains covered and passed.
7. Workspace browser: 9 passes/2 failures; onboarding clicked before its selected
   ICP loaded, leaving an incomplete active workspace for the following check.
   Wait for the real authorized ICP response and assert ACTIVE before proceeding;
   both checks pass. One accidental overlapping fixture launch hit a disposable
   SQLite lock and performed no tests; serialized rerun passed.

Unrestricted `git diff --check` reports whitespace only in pre-existing tracked
generated Gmail output. Source-only `git diff --check -- app docs scripts tests
dashboard ':!dashboard/.next-*'` passes; generated
user work was not discarded. Earlier failures remain in logs and the baseline
records original plus targeted rerun results rather than relabeling old failures.

## Current session source changes

- `app/intent_radar/connectors.py`: approval-sensitive feed cache.
- `tests/unit/test_intent_radar_23.py`: precise URL/authorization denials and cache regression.
- `tests/integration/test_intent_radar_postgres.py`: five isolated PostgreSQL acceptance checks.
- `tests/integration/test_postgres.py`: authorized customer test identity.
- `dashboard/vitest.config.ts`: correct Playwright collection boundary.
- `dashboard/playwright.intent-radar23-platform.config.ts`: existing-platform browser harness.
- `dashboard/auth-e2e/auth.spec.ts`, `dashboard/intent-radar-ui-e2e/journey.spec.ts`,
  `dashboard/workspace-e2e/selection.spec.ts`: precise, current regression contracts.
- `scripts/evaluate_intent_radar_ai.py`, `scripts/verify_intent_radar_23_live.py`,
  `scripts/inspect_intent_radar_23_acceptance.py`: bounded quality/live evidence extensions.
- `scripts/summarize_intent_radar_23_verification.py`,
  `scripts/checkpoint_intent_radar_23.py`: exact evidence export and recovery verification.
- This report, Phase 2/Phase 3 reports, connector matrix, pending report and existing checklist.

## Verified recovery checkpoint

Final immutable location:
`/var/folders/59/jbvs2d7j0yb1229glt7v904c0000gn/T/opencode/intent-radar-23-final-20261111`.
Creator: `scripts/checkpoint_intent_radar_23.py --output <location> --baseline`
the existing `intent-radar-23-20261110T174537734938Z/manifest.json`.

`source.zip` preserves eligible current source including existing unrelated edits;
`verification.zip` preserves exact P2/3 text/XML/JSON results and evidence screenshots.
Both archives are read-back verified against SHA-256 manifests. `manifest.json`
records every source/evidence filename, digest and change since the resume checkpoint;
`intent-radar-23-LATEST.json` identifies this checkpoint. Environment/credential files,
databases and generated builds are excluded. Checkpoint creation does not commit.

The local test cluster is stopped after verification, retaining its disposable
files. No email, commit, push, deployment, production configuration or Phase 4 work.
**Stop here; remaining owner/external gates are explicitly reported.**
