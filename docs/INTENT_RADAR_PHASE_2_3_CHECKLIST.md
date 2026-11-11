# Intent Radar Phase 2–3 restartable checklist

## Full product-audit continuation — 2026-11-11

This narrower historical checklist is retained, but does not account for all
customer requirements. The authoritative detailed continuation is
`INTENT_RADAR_PHASE_2_3_REQUIREMENTS_AUDIT.md` / `.json`: 510 stable IDs, with
remaining missing/partial/unverified requirements individually documented.
Current source checkpoint is the product-audit final manifest recorded in
`INTENT_RADAR_PHASE_2_3_FINAL_READINESS.md`. Supported Node 24 and genuine HN jobs
are now verified; current larger independent quality remains open and the eight
authored live cases failed 7/8 exact categories. See current complete functional
audit/UI/readiness reports before resuming. **Production launch NO-GO.**

Continue the existing modular-monolith implementation; do not reset the checkout.
The uncommitted Gmail/B04, Phase 1 and redesigned UI work predates this task.

## Recovery

- Original source checkpoint: `/var/folders/59/jbvs2d7j0yb1229glt7v904c0000gn/T/opencode/intent-radar-23-20261110T164430742471Z` (1,170 files, readback verified).
- Resume checkpoint: `/var/folders/59/jbvs2d7j0yb1229glt7v904c0000gn/T/opencode/intent-radar-23-20261110T174537734938Z` (1,186 files, readback verified).
- Final checkpoint: `/var/folders/59/jbvs2d7j0yb1229glt7v904c0000gn/T/opencode/intent-radar-23-final-20261111`; source and verification archives are SHA-256/readback verified, with exact filenames and changes in `manifest.json`.
- Creator: `scripts/checkpoint_intent_radar_23.py`; archives exclude environment files, credentials, databases and generated builds.
- Ownership: Intent Radar files and narrow extensions to settings, migrations, shared worker/lifespan and frontend test configuration. Preserve existing Gmail and shared-platform edits.

## Implemented and locally verified — 2026-11-11

- [x] P2-A: additive migration 43, provider capability catalog, workspace-owned approved feed configuration and typed provenance.
- [x] P2-B: expanded official HN feeds/depth-one comments; official Stack Exchange question search; RSS/Atom; approved Discourse public-feed adapter.
- [x] P2-C: bounded multi-source orchestration, per-source history, partial coverage, progressive commits, canonical/native deduplication and relevance penalties.
- [x] P2-D: opt-in scheduling, UTC intervals/IANA display rules, jitter, due-job idempotency, bounded restart recovery and pause/revision fencing.
- [x] P2-E local acceptance: source/cache/signal revocation, lease/cancel/pause concurrency and integrated regressions pass. Commercial Stack Exchange terms review and production Discourse instance approval remain external gates.
- [x] P3-A–C: shared Vertex-first gateway, structured grounded interpretations, budget reservations/cache, selected existing ICPs, versioned scoring, summaries, editable query refinement and customer controls.
- [x] P3-D: reversible workspace feedback and eight-case reproducible English evaluation; initial live Vertex evaluation passed. Broader adjudicated quality evaluation remains pending.
- [x] P3-E local acceptance: backend/frontend/types/build/browser checks and implementation/matrix/pending/verification reports complete. Bundled PostgreSQL 16.15 found outside PATH; 55 isolated PostgreSQL tests pass. Supported Node 24 and broader adjudicated AI quality remain unverified external/runtime gates.

## Prior actual checkpoints, not final acceptance

- Full backend: 781 passed / 51 skipped before later changes.
- Frontend: 141 passed before the latest controls/tests.
- Production frontend bundle passed before latest UI extensions.
- Phase 1 browser regression: 7 passed.
- Phase 2/3 combined browser fixture workflow: 1 passed; source/AI transports were synthetic and are not live-source evidence.
- Live isolated source acceptance: HN Ask/Show, Stack Exchange and W3C RSS; combined check retrieved 65 items. Original URLs/timestamps preserved; cross-tenant reads/writes denied; zero Lead Engine/mail side effects.
- Existing Vertex gateway: eight curated examples classified correctly with exact quotes, one request to the configured `gemini-3.6-flash`; single reviewer, English only.
- Grounded real HN analysis and selected existing ICP completed through Vertex with repeat cache reuse. A validation failure discovered during the first attempt was fixed so rejected output cannot be returned or persisted. Inferred ICP fit now requires review and receives reduced weight.
- PostgreSQL: no `postgres`, `pg_ctl`, `initdb` or `docker` found on PATH. No production credentials used.

## Final actual baseline and stop condition

- Full backend: **808 passed / 56 skipped**, no failures/errors; PostgreSQL subset
  separately **55 passed / 0 skipped**. Combined distinct evidence: **863 passed /
  1 explicit live-mail skip**.
- Frontend **143 passed**; types and isolated production webpack build pass on
  installed Node 26.13.0. Required Node 24 baseline remains unverified.
- **60 distinct browser passes**, including Lead Engine 29, Gmail 2, auth 3,
  workspace 11, customer Sheets 1, Radar 7, Phase 2/3 fixture 1, real-source/Vertex
  1 and redesigned UI 5. Reused unaffected passing cases after targeted repairs.
- Seven genuine public-source checks; HN expanded feeds/replies, Stack Exchange,
  W3C RSS and public Meta Discourse: 94 initial distinct retained signals.
- Live Vertex eight-case evaluation and current-score replay: **0 false-positive
  intent labels / 0 negative scores ≥75**. Single reviewer, English only.
- Source-only diff checking passes. Initial failures and exact repairs remain
  recorded in `INTENT_RADAR_PHASE_2_3_VERIFICATION.md` and verification artifacts.
- Reports: `INTENT_RADAR_PHASE_2_IMPLEMENTATION.md`,
  `INTENT_RADAR_PHASE_3_IMPLEMENTATION.md`, `INTENT_RADAR_SOURCE_CONNECTOR_MATRIX.md`,
  `INTENT_RADAR_PHASE_2_3_PENDING.md`, `INTENT_RADAR_PHASE_2_3_VERIFICATION.md`.
- The disposable PostgreSQL cluster is stopped. No production changes, real sends,
  commit, push or deployment. **Stop. Do not start Phase 4.**
