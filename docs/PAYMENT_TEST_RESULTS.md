# Payment test results — 2026-11-13

This file separates isolated implementation verification from real provider
acceptance. It is not a live-payment or public-launch certificate.

## Current diagnosis — product-scoped restriction

**The current credentials are valid.** The same pair returned HTTP **200** from
both `/v1/payments?count=1` and `/v1/customers?count=1`.
Only subscription operations failed: `GET /v1/plans`, `GET /v1/subscriptions`
and one journaled `POST /v1/plans` returned **401**. The Cloud worker independently
reproduced the Plans 401 using its deployed Secret Manager references. Therefore
an earlier blanket invalid-key interpretation was too broad; do **not** rotate
working keys on that basis. The outstanding issue is Subscriptions API access or
provisioning for the merchant, whose exact account-side cause needs Razorpay confirmation.

In the real Test Mode Dashboard, Subscriptions initially showed Get Started.
That setup entry was opened; after one retry, the Subscriptions dashboard appeared.
The bounded subsequent API list/create attempts still returned 401. No live mode,
financial transaction or legal agreement was accepted during this setup inspection.
The owner reports registering the deployed webhook. Merchant-originated delivery
still needs a genuine subscription event. Read-only endpoint probes alone do not
certify it.

## Earlier scoped plan-list checks

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
**BLOCKED / NOT RUN** until Razorpay permits the subscription operations. Fixture
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

## Subsequent verified checks

The repaired complete isolated suite passed **958 tests**, with one intentional
live-email skip and seven warnings. Real PostgreSQL quota-concurrency and restricted
backup/migration tests were included. Later billing bridge/worker security checks
passed (52-test subset); the complete billing-specific suite now passes **14 tests**.

Both billing browser checks passed: owner catalog/handoff review and mobile
pending/cancelled states. No checkout or provider network was mocked as a real
payment. Both Next.js applications built independently; marketing was not deployed.
Lint reported zero errors and two internal-navigation warnings in the new UI.

A new full source-schema-45 snapshot, SHA-256
`54b1feea0d9c4f6006aa171cdae51f580f02eeae2263dbe3e7122f70428500ea`,
118,441,670 bytes, restored exactly using checksum-verified PostgreSQL 18.7 tools.
A read-only SELECT keepalive preserved the exported snapshot without changing
production transaction/security timeouts. Local migration 45→46 applied once;
a second run applied zero. All **164 original tables' original columns** matched
exactly; no row loss and no differences. Earlier failed rehearsals remain recorded
and were not represented as successful.

## Deployed webhook acceptance

Schema 46 and restricted Test Mode backend commit
`fd4d17ce25c2f644e90bbb6cb6796c5f84ea7d3b` deployed successfully.
Production webhook URL:
`https://leadengine-api-befca7xg4a-el.a.run.app/api/billing/webhooks/razorpay`.
Invalid raw signature returned **400**; valid controlled signature for an unlinked
subscription returned **202 / ignored**. No fake financial record was inserted.
Merchant-originated delivery remains pending owner Dashboard registration.
Final real Razorpay authentication still returned **401**. No real provider
subscription lifecycle acceptance is claimed. Final frontend units: **149 passed**,
including rejected/uncertain creation handling; billing-specific backend: **14 passed**.

## Actual production frontend and owner browser

Vercel deployment `dpl_3Ngj5ooQM2Ea8jz7uKjHk7F19x1T`, commit
`7bda1d65db8a462f64525a26910bce82f54e76bd`, was promoted through the existing
project. The real authenticated owner browser loaded `/billing`, showing internal
Test Mode catalog fixtures, no subscription, no verified payments and disabled
checkout while provider mappings remain absent. This verifies the actual deployed
read interface; it does not imply successful checkout.

## Current acceptance update — 2026-11-14 (supersedes earlier blockers)

The earlier product-specific restriction has resolved. The same current Test keys
returned **200** from Payments, Plans and Subscriptions. No key rotation was
needed. Three real internal test plans were created/verified and mapped through
the journaled preparation script. The earlier zero-plan figures describe failed
attempts only, not current state.

One real controlled Starter subscription was created through the deployed API.
A repeat using the same request ID returned the same subscription. The actual
Vercel checkout opened Razorpay's official SDK with its Test Mode banner. The
owner completed the final authorization step using the documented sandbox card.
The browser reached the success route only after the deployed verification handler
returned successfully. Independent production reconciliation persisted **one
captured Test Mode payment** against the matching paid invoice and active current
period. This is genuine sandbox evidence, not a fixture or a real-money payment.

As of the first post-checkout read, the merchant webhook ledger contained zero
receipts for this controlled subscription. Owner registration is reported but
actual delivery remains under investigation. Renewal, failed-charge recovery,
cancellation and actual merchant replay are not yet claimed as passed.

Local worker optimization now excludes terminal mandates from periodic polling,
while signed late events still reconcile them. All **16 billing tests pass**,
including active recovery, terminal exclusion and late signed event processing.
This change is not represented as deployed until a verified rollout is recorded.
