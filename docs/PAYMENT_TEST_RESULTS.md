# Payment test results — 2026-11-13

This file separates isolated implementation verification from real provider
acceptance. It is not a live-payment or public-launch certificate.

## Real Razorpay Test Mode

Credentials were loaded from the existing root `.env` in memory. The key ID has
the Test Mode prefix. A minimal authenticated `GET /v1/plans?count=1` returned
**HTTP 401**. The owner supplied a corrected pair; the bounded retry still returned
401. No duplicate names, surrounding whitespace, swapped fields or placeholder
values were detected. No credential values are included in this report.

The internal plan preparation script stopped on authentication failure. **Zero
plans, subscriptions or charges were created by these attempts.** No key rotation
or multiple-account workaround was implemented.

Real subscription creation, Checkout authorization, successful/failed Test Mode
payments, renewal, cancellation and merchant-originated webhook delivery are
**BLOCKED / NOT RUN** until Razorpay accepts the configured credentials. Fixture
results below do not count as successful provider acceptance.

## Isolated verification

Initial billing unit set: **8 passed**. Extended raw webhook/security/lifecycle
set after correcting test startup isolation: **11 passed**. The initial expanded
test incorrectly changed the test application's environment before startup; it
has been fixed to keep startup on the isolated SQLite fixture and test production
request authentication only afterward. No production DB write occurred.

Existing Radar/Growth/MCP subset: **53 passed**. Repaired account/setup/customer
regression subset: **61 passed**. The full first billing backend run had
**943 passed, 11 failed, 1 intentional live-mail skip**; it is not a release pass.
Failures concerned account/onboarding error-order preservation, explicit existing
Lead Engine fixture grants and an outdated PostgreSQL dump-tool selection.
Those repairs require a subsequent complete frozen run before release.

Frontend: **148 unit tests passed**; optimized Next.js build passed after fixing
the preserved Lead Engine overview type reference. Two isolated Growth browser
checks passed through the real signed local gateway and persisted leased jobs.
Their AI/source data are synthetic fixtures, not independent AI evaluation.
Billing desktop/mobile acceptance and final migration/release checks are recorded
below when actually completed.

## Recovery

The first fresh schema-45 production snapshot was created read-only, but restoring
with the private PostgreSQL 18.6 tools failed on `pg_attver`. No production migration
was applied. PostgreSQL 18.7's release documents the internal attribute versioning
change; the local tools are being upgraded from checksum-verified official source.
Do not strip arbitrary schema statements or claim this failed restore passed.

See [PostgreSQL 18.7 release](https://www.postgresql.org/docs/release/18.7/)
and [attribute catalog](https://www.postgresql.org/docs/18/catalog-pg-attribute.html).
