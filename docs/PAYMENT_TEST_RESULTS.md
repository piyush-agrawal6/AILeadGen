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

### Genuine failed-renewal simulation

The merchant Test Mode dashboard exposed `Charge this now`, explicitly labeled
as a test simulation with success/failure outcomes. `Charge as failure` returned
`Charge marked as FAILURE` and created an issued/unpaid invoice. Production
reconciliation retained the original captured-payment history, advanced to the
provider's returned period and cleared `paid_start`/`paid_end`. Therefore
`settled_current_period=false`; no sandbox paid entitlement remains. The provider
continued reporting `active`, illustrating why that status alone is insufficient.
No live charge or direct financial database write was made. Merchant subscription
webhook receipts remain absent at this checkpoint.

### Image-only patch deployed

Commit `e82ce0d59dbb074fbedaf854f353e9dfbc7129f7` built successfully in Cloud Build
`39bc751e-6ea5-45c4-a986-3dac8c2e5d00`; both image dependency checks passed.
Existing API revision `leadengine-api-00128-faq` now serves the patch, with matching
worker images. Only images changed: identities, commands, environment/Secret
Manager references, scheduler configuration and disabled delivery/registration
flags were compared and preserved. **No migration ran; schema remains 46.**
Five signed/read smoke routes passed HTTP 200. The patch's focused billing and
release-security set passed **56 tests**, including 16 billing cases. Terminal
polling exclusion and safe ignored-event diagnostics are now deployed.

### Webhook diagnosis and live security

Safe deployed diagnostics observed actual `payment.authorized`, `payment.captured`,
`order.paid` and `invoice.paid` notifications. The restricted subscription handler
intentionally ignores those event types. No required `subscription.*` delivery
has yet been verified. The URL and shared signing secret work; the merchant event
selection still needs inspection/correction. Do not rotate working credentials.

All nine live non-destructive security checks passed: health, unsigned denial,
signed owner access, untrusted CORS denial, nonce replay denial, unapproved actor
denial, invalid signature denial, private OpenAPI denial and oversized-body denial.
The post-patch endpoint probes also passed invalid HMAC 400, signed unlinked 202
ignored and adjacent-route 401. One controlled subscription, one independently
verified payment and three mapped test plans are present. Real sending is false;
manual owner Lead Engine and Intent Radar grants remain intact.

### Missed-history repair and fresh database checks

The real provider history contains a captured renewal payment for its second
period. Subsequent accelerated charge attempts fail with the provider's exact
reason `card_mandate_current_cycle_allowed_debit_exceeds`; further charge attempts
have stopped. Correctly signed `subscription.pending` events now arrive and are
processed once each by the deployed reconciliation worker.

Acceptance exposed a real catch-up gap: pending subscriptions previously skipped
paid invoices from earlier periods if their successful event had been missed.
The repair independently verifies bounded historical invoices/payments, persists
their own periods and grants access only for verified active current settlement.
At most three payment reads occur per pass; existing history is reused and current
settlement is prioritized/revalidated. Provider I/O retains no idle database
transaction. No paid row is manufactured directly.

The focused suite passes **73 tests**, including 18 billing tests. Both actual
local PostgreSQL billing checks pass, including concurrency and history catch-up.
The first local rerun could not start because yesterday's test server was absent;
a new instance initially defaulted to SQL_ASCII, causing bytes/text fixture errors.
That unsuitable run was stopped. A separate fresh UTF-8 test database fixed the
environment; one missing import in the new test was also corrected. No production
database was changed. The full frozen UTF-8 suite is running; this repair is not
yet represented as deployed.

### Wider regression triage

The first complete UTF-8 rerun finished with **955 passed, 11 failed, 1 skipped**.
Those failures were reproduced and classified, not ignored. Eight older existing-
customer workflow cases lacked an explicit Lead Engine grant under the new default-
off enrollment policy. Their shared existing-customer fixture now grants that
product explicitly; new-customer denial tests and production guards remain intact.
Three mail worker outcome tests depended on the real weekday and failed on Saturday.
They now use explicit business-time clocks. A new weekend test confirms sending
still stops before delivery and leaves the ready item intact.
The repaired customer/billing regression set passes **80 tests**. A fresh complete
frozen rerun is in progress; the earlier failed run is retained as evidence.

### Billing UI refresh acceptance

A real browser inspection exposed stale status after external provider updates.
The UI now refreshes on tab focus and every 30 seconds only while an open mandate
exists and the page is visible. Requests support cancellation; mutation outcomes
invalidate only the owned billing and product-access caches. Frontend units pass
**151 tests**, the isolated production build passes, and both desktop/mobile billing
browser checks pass. This UI repair is not yet represented as deployed.

### Final frozen regression result

After the explicit entitlement and clock fixture repairs, the full UTF-8 backend
and PostgreSQL suite passed **967 tests**, with **1 intentional live-email skip**
and 7 recorded warnings, in 418 seconds. Backend source fingerprint matches the
prepared `65718d8d0f0cff4dc1dd5b83af82a3921ce210c1` image source. The failed earlier
runs remain recorded and are not presented as passes. No production access checks
or weekend sending protections were weakened.

Real existing Gmail preservation checks passed **SMTP READY / IMAP READY**,
sync enabled, sending disabled, **zero emails sent**. The history patch rollout
and final controlled cancellation are being verified separately.
