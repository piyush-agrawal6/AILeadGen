# Intent Radar subscriptions — restricted release checkpoint

**LIMITED GO for the approved owner beta; NO-GO for public paid subscriptions.**

Existing backend deployment is live at
https://leadengine-api-befca7xg4a-el.a.run.app, revision
`leadengine-api-00126-qox`, source
`fd4d17ce25c2f644e90bbb6cb6796c5f84ea7d3b`, additive schema 46.
The migration followed exact backup/restore and all-original-column preservation.
Existing API/worker identities, Gmail, manual grants and customer data are preserved.

Verified public webhook URL:
https://leadengine-api-befca7xg4a-el.a.run.app/api/billing/webhooks/razorpay

Actual signature probes passed (invalid 400, valid unlinked 202/ignored). Dashboard
registration and genuine merchant deliveries remain pending. Exact events and
separate secret configuration are in RAZORPAY_INTEGRATION.md.

Real Razorpay API authentication is **BLOCKED: HTTP 401**, including the final
request after the owner corrected credentials and backend Secret Manager setup.
No plans, subscriptions or charges were created by failed attempts. Successful and
failed payments, actual renewal/cancellation and paid-entitlement activation are
**NOT RUN**. Isolated fixtures do not substitute for these gates.

Implemented: strict server catalog/mode separation; owner-managed creation;
unknown-outcome recovery without duplicate mandates; official Checkout integration;
server-owned signature validation; independent invoice/payment verification;
durable signed/idempotent webhooks; bounded existing-worker reconciliation;
workspace/cycle quotas and capacity; safe marketing plan-intent handoff; retained
Lead Engine grants with new public enrollment disabled. In-place proration/live
mode/public checkout remain unavailable. Growth Intelligence stays inside Intent Radar.

Verified tests: full backend **958 passed / 1 intentional live-mail skip**;
additional billing suite **14 passed**; frontend **149 passed**; optimized SaaS and
independent marketing builds passed; two billing and two Growth browser checks
passed using isolated signed-backend fixtures. Real owner Growth browser acceptance
also passed. See PAYMENT_TEST_RESULTS.md for initial failures and subsequent repairs.

Remaining owner actions: supply an active matching Razorpay Test Mode API pair
that the provider accepts; register the verified webhook with the existing separate
secret and listed events; complete genuine sandbox lifecycle acceptance; arrange
the approved independent human reviewers/adjudicator. Commercial pricing and live
payment authorization are separate future approvals. Do not enable unrestricted
registration or represent the independent AI evaluation as passed.
