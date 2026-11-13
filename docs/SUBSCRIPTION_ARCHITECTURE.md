# Subscription architecture

One modular monolith, existing PostgreSQL, existing Vercel dashboard and Google
Cloud API/worker infrastructure. Marketing remains an independent deployment.
Growth Intelligence is part of `INTENT_RADAR`; it is not another billed product.

Additive migration 46 adds subscriptions, workspace/mode slots, provider plan
mappings, customer mappings, payments, signed webhook receipts, cycle usage,
idempotent reservations and bounded action windows. Historical customer,
contact/suppression, campaign and migration records are preserved.

Each mutation re-resolves verified membership and requires OWNER. Administrators
may review billing; members/viewers cannot manage payments. Subscription lookup
uses both local UUID and current verified workspace. Provider IDs are server-owned.
Test/live identities and uniqueness are mode separated; only Test Mode is currently
accepted. Client prices, periods, workspace IDs and arbitrary return URLs are not
accepted. Entitlements derive from independently reconciled settlement rather
than client redirects or raw webhook state. Manual organization-product grants
remain independent; cancellation never deletes or revokes them.

Upgrade/downgrade proration is deliberately unavailable. The working supported
flow cancels the existing sandbox mandate before choosing another plan. Enterprise
requires an approved custom agreement, not a decorative checkout button.

Rollback: disable billing, retain migration/data, use a schema-46-compatible API
and workers with billing disabled and the previous Vercel build. Never roll a
schema-45-only binary onto schema 46 or downgrade/drop tables. A billing-disabled schema-45/46 compatible API and workers are promoted before
DDL; billing-enabled startup requires schema 46. Production migration
requires a fresh schema-45 snapshot, exact restore, migration idempotency and
original-column preservation proof; earlier 44→45 evidence does not substitute.
