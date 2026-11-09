# HeySow engineering requirements

Apply the owner-provided engineering standards throughout this repository.
Begin with `docs/ENGINEERING_STANDARDS_AUDIT.md` and the domain-specific standards
linked by `docs/NEW_MODULE_CHECKLIST.md`. Distinguish implemented behavior from
planned capabilities; documentation and UI labels are not evidence of readiness.

- Preserve the modular monolith and working provider/session integrations.
  Reuse shared platform services; add infrastructure only for measured needs.
- Resolve workspace membership server-side. Scope resources, caches, jobs,
  attachments and integration access to that verified workspace. Test absent
  context and cross-workspace access. Never weaken isolation to pass old tests.
- Disabled modules must be inaccessible through direct APIs and workers, while
  their historical data remains intact. Do not advertise unavailable modules.
- Use versioned, recovery-tested migrations. No production reset, truncation or
  broad deletion. Operational cleanup requires a scoped dry run, a fresh backup,
  a tested restore and preservation of contact history and suppression records.
- Keep secrets server-only. Never print credentials or copy them into frontend
  code. Current work must not modify `.env`, OAuth credentials or production
  deployment settings without the owner's applicable authorization.
- Use bounded asynchronous work for expensive operations, with timeouts,
  cancellation, safe retries and idempotency. No unbounded provider spending.
- Keep Google authentication real; do not add mock signup/recovery/invitation
  actions. Public signup remains blocked until tenant and integration isolation
  are implemented and validated.
- Follow the current cleanup workflow: company/ICP qualification is distinct
  from contact availability and send eligibility. Internal five-template
  experiments and mandatory static PDFs are not the default SaaS workflow.
- Run meaningful isolated tests and appropriate builds. Critical security,
  data-integrity and regression failures block release. Record actual failures;
  never claim production readiness, scale or successful acceptance without evidence.
- Check the nearer `AGENTS.md` before editing a subdirectory. In particular,
  read the bundled Next.js documentation required by `dashboard/AGENTS.md`.
