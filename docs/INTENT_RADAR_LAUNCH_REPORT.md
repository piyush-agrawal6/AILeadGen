# Intent Radar launch report — current release checkpoint

**LIMITED GO: existing approved owner beta. NO-GO: public paid launch.**

Production frontend: https://app.planebyte.com (existing Vercel project).
Backend: https://leadengine-api-befca7xg4a-el.a.run.app (existing Google Cloud Run).
Marketing, PostgreSQL data, Gmail identities and production login allowlist are
preserved. No frontend hosting migration, real email or live payment is enabled.

Verified live Growth frontend commit:
`35ecb9da8c0a59b149009a50437c40d0c5edd621`, Vercel deployment
`dpl_Dga3Lqgt2rFGQf3RCWu98PFo1s5N` promoted successfully.
Verified live backend commit: `982a499d3213cf93e9673b7e2777293757645f60`,
revision `leadengine-api-00122-tug`, schema 45, zero additional migrations.

Real owner browser acceptance observed the authenticated PlaneByte workspace's
Growth Intelligence overview with 6 collected discussions, 5 opportunity candidates,
1 active monitor and 2 stored themes. UI explicitly stated insufficient comparable
history and did not present market growth or purchase probabilities as proven.
Earlier real Vertex research, exact citations/exports, scoped MCP and idempotent
scheduled watchlist evidence are recorded in the Phase 4 report. The controlled
acceptance watchlist was paused afterward.

New billing and Intent Radar-primary navigation are under local verification and
are not yet represented as deployed. Test Mode API authentication currently returns
401; real billing acceptance remains blocked. Public paid checkout and public
registration remain closed. Existing authorized Lead Engine access is preserved;
new enrollment is disabled by the new server policy once this release is deployed.

The approved 120-case independent AI evaluation is prepared but **not passed**:
two independent reviewers and an adjudicator have not been supplied; minimum source
family/industry coverage and cost/quality gates remain outstanding. Do not fabricate
human review or call the product a fully validated unrestricted SaaS.

Remaining owner actions: correct the matching Razorpay Test Mode key pair; configure
the exact deployed webhook URL and matching independent secret after endpoint
verification; arrange the approved reviewers/adjudicator; approve commercial pricing
and live billing separately if a later paid launch is desired.

## Billing backend rollout verified

Backend release commit `fd4d17ce25c2f644e90bbb6cb6796c5f84ea7d3b` is live as
`leadengine-api-00126-qox`. A billing-disabled compatible API/worker bridge was
promoted first (`leadengine-api-00124-wiz`), then the recovery-tested additive
migration 45→46 was applied once. Existing workers use the matching committed
image, with existing identities/commands preserved. The existing Intent Radar
scheduler was restored to its previously enabled state; outreach/acquisition
schedulers and real email remain disabled. No frontend Cloud Run service was added.

Verified webhook:
https://leadengine-api-befca7xg4a-el.a.run.app/api/billing/webhooks/razorpay

Actual HTTPS probes: invalid signature **400**; correctly signed unlinked controlled
probe **202**, safely ignored. This is endpoint security acceptance, not a real
merchant webhook, payment or paid entitlement. Test Mode secrets are backend-only
Secret Manager references. Only the previously verified owner workspace is enabled
for sandbox billing. Public checkout remains false and live mode is rejected.

A final real Test Mode plan-list authentication request still returned **401**.
Three internal plans, real subscriptions, payments, renewals and cancellations
remain unverified/blocked. The owner has received the exact webhook URL, ten event
names and the instruction to match the server-only webhook secret. No test
subscription or payment was fabricated to make the production ledger look ready.
