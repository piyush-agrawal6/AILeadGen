# PlaneByte production release report

## Checkpoint — November 15, 2026

The redesign and second backend fix are currently local and unpromoted. Do not confuse a successful build with a live release.

- Main serving API: `leadengine-api-00138-suf`, source `0077fe32d1a0dc8b36daec38be03d0d89980c452`.
- Earlier staged API: `leadengine-api-00140-riz`, source `cda3249b4fcdf8319b061660f878e4545c08c5ac`, zero main traffic. Its images were staged to the three existing worker jobs; runtime settings were preserved.
- Earlier frontend candidate: Vercel `dpl_acj6AQvze7qVDBQm27Mb5CZnM3LW`, READY, not assigned to `app.planebyte.com`.
- Existing frontend domain: Vercel `dpl_FtEzeN1F8dzQhw2XFda54nrMabwX`, source0077fe3.
- Marketing remains on existing Netlify deployment `6af8808515984dc64ea4c39c`, repository commit `04ff0901368603c259d79a98c934b50164913d30`.

Current local production frontend build passes. Backend frozen verification:1,065 passed / one explicit live-mail skip. Latest UI units/browser checks and screenshot review are still running. A previous browser attempt could not bind the local test ports under the default process restrictions; it was rerun using the authorized local test-server permission. No test failure was relabeled as a pass.

## Release gates

Commit exact tested source, build locked backend images, stage without traffic, verify deterministic counts and one bounded real research worker/export/replay journey, measure reads under concurrency, then promote matching backend and Vercel source only when critical checks pass. Preserve existing settings, schedulers, production data, Google credentials and provider gates.

Fresh backup/restore evidence: `data/backups/beta-recovery-20261114T173117Z/production.dump`, SHA256 `bb4e5fe758ed214ad0390be1a45a210e57aa007a87d1364e07f723dadc9aa806`. Full original table fingerprints matched the local restore; local46→47 was idempotent with zero row loss. Production remains schema46; no production migration/reset/delete was run.

Public signup, real outreach and live recurring checkout remain closed. Owner actions still concern merchant recurring capabilities, source/publisher permissions and genuine independent reviewers. No new permission is needed for the already authorized reversible implementation and verification work.
