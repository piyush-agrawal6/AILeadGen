# Intent Radar subscriptions — restricted release checkpoint

**LIMITED GO for the approved owner beta; NO-GO for public paid subscriptions.**
Updated 2026-11-14. This remains an acceptance checkpoint, not a completed
subscription-lifecycle certificate.

## Verified production

Frontend https://app.planebyte.com uses the existing Vercel project, deployment
`dpl_3Ngj5ooQM2Ea8jz7uKjHk7F19x1T`, source
`7bda1d65db8a462f64525a26910bce82f54e76bd`.
Backend https://leadengine-api-befca7xg4a-el.a.run.app is revision
`leadengine-api-00126-qox`, source
`fd4d17ce25c2f644e90bbb6cb6796c5f84ea7d3b`, additive schema 46.
Existing workers use that matching backend source. No hosting migration,
marketing deployment, public signup, prospect scan or real outreach was performed.

The exact schema-45 backup restored successfully, migrated locally once to 46,
then applied zero migrations on replay. All original columns in 164 tables were
preserved exactly before the production additive migration. Manual product grants,
customer history, Gmail and existing runtime identities remain intact.

## Real Razorpay Test Mode progress

- Payments, Plans and Subscriptions APIs: **HTTP 200**. The earlier product-scoped
  401 restriction is resolved; existing working keys were retained.
- Three internal Starter/Growth/Scale test plans: created, independently verified
  and mapped. Prices are integration fixtures, not approved commercial offers.
- One owner-controlled Starter subscription: created; same-request replay returns
  the same mandate, without duplicate creation.
- Real deployed Checkout: opened with Test Mode banner; owner completed sandbox
  authorization. The actual signature handler returned successfully.
- Independent settlement: one captured Test Mode payment, matching paid invoice
  and active current subscription period verified in production persistence.
- Merchant webhook receipt, renewal, failed-charge recovery and cancellation:
  acceptance still in progress. Do not infer these from initial payment success.

Public webhook, deployed and raw-signature-tested:
https://leadengine-api-befca7xg4a-el.a.run.app/api/billing/webhooks/razorpay

Invalid signature returned 400; correctly signed unlinked probe returned
202/ignored. The owner reports Dashboard registration complete. These controlled
probes are distinct from actual merchant delivery.

## Verification and restrictions

Full isolated backend: **958 passed, 1 intentional live-mail skip**; frontend:
**149 passed**; optimized SaaS and independent marketing builds passed. Two billing
and two Growth browser checks passed with isolated signed-backend fixtures.
Real owner Growth and billing browser read acceptance passed. Subsequent terminal
polling regression: **16 billing tests passed** locally; deployment of that small
worker optimization is tracked separately. No production polling claim is based
on an unshipped local change.

Only the verified PlaneByte owner workspace is approved for Test Mode billing.
Public checkout and live mode are blocked. Lead Engine remains available to its
previously authorized owner at `/lead-engine`; new enrollment is disabled.
Growth Intelligence stays inside Intent Radar.

The approved independent 120-case AI evaluation remains **not passed**: two human
reviewers and an adjudicator are still required. Commercial pricing/live payment
authorization are separate future approvals. No unrestricted public launch is
certified while critical acceptance gates remain outstanding.

## Subsequent verified patch and failure acceptance

Backend/worker source is now `e82ce0d59dbb074fbedaf854f353e9dfbc7129f7`, API revision
`leadengine-api-00128-faq`. The image-only rollout preserved configuration,
identities, secrets, schedulers and schema 46; no migration ran. All five deployed
read/safety smoke checks returned 200. The focused release-security suite passed
56 tests, including all 16 billing tests.

A genuine provider Test Mode failed-charge simulation completed. The unpaid
advanced period has no verified settlement, so paid-period fields and sandbox
billing entitlement were cleared; original payment history remains. Merchant
subscription webhook delivery, successful renewal and cancellation remain to be
completed before claiming full Test Mode lifecycle acceptance.
