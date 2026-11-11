# Intent Radar Phase 2 implementation and acceptance

## Independent product audit follow-up — 2026-11-11

The historical scoped completion claim below is preserved as prior evidence,
**superseded for full product acceptance** by
`INTENT_RADAR_PHASE_2_3_REQUIREMENTS_AUDIT.md` and
`INTENT_RADAR_PHASE_2_3_COMPLETE_FUNCTIONAL_AUDIT.md`. The full 510-criterion audit
finds incomplete cursor/retry/accounting/retention and global paging/filtering
contracts. Stale local Phase 1 API, source labels/filter, monitor history,
opportunity detail and actual hard-kill source checkpoint recovery were repaired.
Current backend: 822 passed; isolated PostgreSQL: 56 passed; Node 24 build/types
pass. Genuine HN opt-in jobs are now accepted. Source approval and staging remain
gated; **full Phase 2/3 commercial launch is NO-GO**.

### Preserved prior report

Verified locally on 2026-11-11, continuing the existing uncommitted implementation.
**Local implementation and acceptance are complete; commercial activation is gated.**
See [final verification](INTENT_RADAR_PHASE_2_3_VERIFICATION.md),
[connector matrix](INTENT_RADAR_SOURCE_CONNECTOR_MATRIX.md) and
[remaining gates](INTENT_RADAR_PHASE_2_3_PENDING.md).

| Completed feature | Actual implementation | Verification |
|---|---|---|
| Additive storage and capability catalog | Ordered migration 43 (`intent_radar_23_schema.py`), workspace-owned source configurations/cache/runs; migrations 41/42 retain Phase 1 and fencing | SQLite upgrade, idempotency, backup/readback restore and suppression-history preservation; 55 real PostgreSQL checks including applying the current migrations |
| HN expansion | Official v0 Ask/Show/New/Top/Best, opt-in jobs, round-robin selection and depth-one replies, 22-request ceiling | Genuine Ask and Show: 20 items/21 requests each; combined New/Top/Best with replies: 19 items/22 requests |
| Stack Exchange | Official 2.3 question search, configured sites/tags/dates, first page capped at 20, server-only optional application key, license attribution | Genuine Python query: 20 items/1 request, quota remaining 299; transport shape, cache/backoff and log-redaction tests |
| Approved RSS/Atom and Discourse | HTTPS operator allowlist, public-DNS/URL validation, no redirects/authentication parameters, bounded XML parsing, explicit publisher reference/attribution | Genuine W3C and Meta feeds; RSS/Atom, ETag/304, malformed/DTD/entity/size denial and per-feed partial-failure tests |
| Multi-source collection | Bounded sequential shared job, per-source history, partial coverage, progressive commit, native/canonical identities | Genuine combined run: 65 scanned items; synthetic source failure tests; repeat/native dedupe; zero prospect/mail side effects |
| Scheduling | Opt-in saved monitor, UTC fixed intervals/IANA display, up to 299 seconds deterministic jitter; minimum 12 hours by default | Due-job idempotency, pause/revision and membership denial; real browser manual clock advance; PostgreSQL expired-worker recovery |
| Quotas and recovery | Workspace/global daily search counts under shared transactional lock, monitor cap, durable cooldowns, shared bounded attempts/leases | Quota, rollback persistence, duplicate execution, retry exhaustion, cancellation and lease-replacement/expiry tests |
| Revocation safety | Adapter cache fence and progressive persistence fence recheck membership, product, job lease, monitor revision and source configuration | Eight response/persistence boundary cases plus atomic authorization tests; three PostgreSQL independent-connection revocations |
| Frontend integration | Capability-driven source/feed/ICP selection, schedule controls, source health/configuration, usage and run history | 143 frontend units, types/build and 60 distinct relevant browser checks |

## Repairs made during final acceptance

- Provider denial tests now distinguish HTTPS-shape `ValueError`, unapproved-host
  403 and public-destination/auth-parameter 422. A positive public-DNS case prevents
  blanket denial from passing. Viewer authorization is checked before URL handling.
- Feed caches now include an exact configuration digest. Approval/endpoint/
  attribution/retention edits cannot reuse old content or conditional validators.
  A targeted test verifies both valid repeat reuse and changed-endpoint refetch.
- Vitest excludes the existing Playwright UI directory; those browser checks run
  through Playwright. No assertions or permission checks were removed.

Existing Gmail/B04 and shared-platform changes were preserved. No Phase 4 work,
production changes, real emails or database resets occurred. HN jobs remain opt-in;
that branch was inspected, but a genuine job-feed request was not part of acceptance.
