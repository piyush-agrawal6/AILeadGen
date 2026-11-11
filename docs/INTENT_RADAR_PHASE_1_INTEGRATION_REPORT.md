# Intent Radar Phase 1 integration checkpoint — 2026-11-10

**Local implementation and available verification complete.** PostgreSQL remains
blocked, not passed. Lead Engine remains paused and can resume from its B04 handoff.
Original dirty files were preserved. No deployment, commit/push, environment/OAuth
change, database reset, production operation or real email occurred.

All evidence below is under `data/artifacts/verification/intent-radar/`.

| Check | Exact result | Evidence |
|---|---|---|
| Full backend/API/security/regressions | **757 passed, 51 skipped**, zero failures/errors; 7 warnings | `backend-final.log`, `backend-final.xml` |
| Focused security/workers/invitations | **54 passed** | `security-workers.log`, `.xml` |
| Frontend units | **134 passed**, 35 files | `frontend-corrected-final.log` |
| Frontend type checking | **Pass** | `typecheck-verified.log` |
| Isolated production bundle | **Pass** | `build-final.log` |
| Integrated Intent Radar browser journeys, production bundle | **4 passed** | `browser-production-final.log`, `browser-results.json` |
| Lead Engine browsers, production bundle with Radar grant present | **29 passed** | `lead-engine-browser-final.log`, `lead-engine-browser-results.json` |
| Real Hacker News fetch/service/worker | **Pass: 21 requests, 12 signals, 12 alerts** | `live-hn.log` and retained disposable database |
| Git whitespace check | **Pass** | `git diff --check` |

The 51 skips are 50 opt-in PostgreSQL cases and one deliberate live-mail case.
Local PostgreSQL connection was refused; PostgreSQL/Docker tooling is absent.
No production DSN or new infrastructure was used to bypass this blocker.

## Browser and source evidence

Browser tests use real Next/Auth.js fixture-signed sessions, signed gateway calls,
FastAPI, SQLite and workers. Only their HN transport is synthetic and labeled;
browser fixtures do not establish live provider readiness. They cover product
switching, inert wizard save, pause/resume, manual discovery/repeat dedupe, original
evidence, rapid status/note updates, saved collections, opportunity edits, alert
acknowledgment/shared notices, monitor edit/duplicate/archive/restore, cancellation,
cross-workspace/cache denial, unavailable product/direct APIs and 1440/390/320px views.

Separate real HN acceptance used the official public API without fixtures or AI:
`https://news.ycombinator.com/item?id=50433412`, **“Ask HN: What should a stranger
know first about your unfinished project?”**, observed `2026-11-09T22:48:13+00:00`.
Saved/opportunity persistence and cross-workspace denial passed; zero company,
contact, workflow or email records were created. Database retained at
`/var/folders/59/jbvs2d7j0yb1229glt7v904c0000gn/T/opencode/intent-radar-live-20261110-resume.db`.
This verifies recent Ask HN fetching, not purchasing intent or historical coverage.

## Failures found and repaired

- Initial full backend: **749 passed, 2 failed, 51 skipped**. Rejected Gmail refresh
  now clears ciphertext under the existing revision/lease/tenant fence. A legacy
  mailbox test now explicitly disables customer Gmail and asserts its actual 503
  gate while retaining the internal-sync 409 ownership denial. Final suite is green.
  An earlier 120-second run was interrupted and is not acceptance evidence.
- Type checking rejected six Testing Library `exact` options; corrected selectors.
  Adding the browser directory exposed Vitest collecting Playwright tests; its
  explicit browser exclusion was added. Final units/types pass.
- Browser integration found the shared notification model rejected `INTENT_RADAR`
  with HTTP 500. The contract/UI now support Radar, acknowledge owned notices and
  hide unavailable-product notices without deleting history.
- Rapid status/note edits exposed stale revisions and premature control enablement.
  Notes use current evidence revision; mutations await read invalidation and signal
  controls remain pending through refresh. The actual rapid-edit browser passes.
- New browser harness startup/path mistakes and ambiguous labels/navigation races
  were corrected; intermediate logs remain. Development Lead Engine run: **26 pass,
  3 fail** (dev CSP plus archive response status). First production run: **27 pass,
  2 fail**. Disabled archives now return 404 before shell streaming; strict security
  assertions were retained. Final production run: **29 pass**.

## Reproduce and resume

- Backend: `.venv/bin/python -m pytest tests -q`.
- Frontend: `npm run typecheck`; `npm run test -- --maxWorkers=2` in `dashboard/`.
- Use the exact fixture build command/environment in `build-command.json`; output is
  `.next-intent-radar-build`. No production settings are needed.
- Radar: `INTENT_RADAR_BROWSER_PRODUCTION=1 npx playwright test --config=playwright.intent-radar.config.ts`.
- Lead Engine: `npx playwright test --config=playwright.intent-radar-regression.config.ts`.
- Checkpoint: `source-checkpoint.zip` preserves all dirty tracked/untracked source,
  original changes and Git diff/status; `source-checkpoint.json` records hashes,
  result counts and successful archive readback. Generated Next directories are
  ignored, retained locally and excluded from the source checkpoint.

**Lead Engine next action:** resume B04 frontend/broader mailbox-worker/API closure
from `LEAD_ENGINE_PHASE_1_TO_6_COMPLETION.md` lines 420 onward. Review the narrow
refresh-secret fix in `app/integrations/service.py`, notification contract in
`app/platform/invitations.py` and archive pre-render denial in `dashboard/proxy.ts`.
Keep schema 40 and additive 41–42; do not reset/reapply from scratch or recalculate
the roadmap completion percentage from these Radar results. Customer Gmail,
external integrations and PostgreSQL/live acceptance are still separate work.
