# Billing entitlements and usage

Public paid checkout is closed. Test settlement grants only a restricted sandbox
Intent Radar entitlement to explicitly approved workspace IDs. It never becomes a
live paid subscription or grants Lead Engine/Search Visibility. Manual/beta grants
are preserved and continue to use existing operator safety budgets independently.

The backend's one catalog defines Starter, Growth, Scale and Enterprise/custom.
Prices and limits can be configured server-side; default INR amounts are explicitly
internal Test Mode fixtures. No Intent Radar commercial price is approved.
`BILLING_CATALOG_JSON` can supply a strictly validated complete catalog, with
optional existing `RAZORPAY_TEST_PLAN_ID_*` mappings. The dashboard renders backend
values; it owns no price table. Provider price/period/currency/quantity are verified.

Plan dimensions: searches, AI calls, reserved AI tokens, monitor count, monitor
executions, saved opportunities, active team members and API/MCP requests. Existing
global/day/provider safety caps remain in force in addition to plan limits.
Atomic workspace-locked reservations use stable operation IDs; retries cannot
spend the same search/opportunity twice or alter its reserved amount. AI provider
attempts reserve fresh upper-bound capacity. Actual billed tokens remain separate.
Cycle buckets use verified provider invoice/current-period bounds, never browser
input or a guessed calendar month. Renewals create a new bucket and preserve old
history. Failed, halted, paused, expired, inconsistent or unverified settlement
provides no subscription grant. A single test payment never creates unlimited use.

Independent billing quota, PostgreSQL concurrency, lifecycle, revocation and
cross-workspace tests must pass before rollout. Real Razorpay acceptance is
reported separately from fixtures in PAYMENT_TEST_RESULTS.md.
