# Product release and commercial billing — in progress

The non-chargeable product/approved-pricing changes have passed their frozen
local gates:998 backend passes,1 intentional live-mail skip,159 frontend unit
passes, successful TypeScript/build and7 product browser passes across six
viewport sizes. Lead Engine implementation, historical data, Gmail safeguards,
membership checks, admission restrictions and old payment records are retained.
The previous verified checkpoint contains no migration. The current approved-allowance update includes additive migration47; production application requires fresh recovery and compatible-image rollout first.

Production deployment IDs and post-rollout measurements must be added after
actual deployment. Existing production API revision is`leadengine-api-00135-paw`;
its overview/saved/source-health latency remains a measured P0 issue. Do not
mistake local read-budget tests or the Vercel build for production acceptance.

## Architecture

- SaaS frontend: existing Vercel project, `https://app.planebyte.com`.
- API/workers: existing Cloud Run resources in`querryside`, `asia-south1`.
- PostgreSQL: existing schema46; no reset, data removal or migration here.
- Marketing pricing: existing Planebyte-Landing repository/Netlify site,
  `https://planebyte.com`, as newly authorized by the owner pricing brief.

## Financial status

Approved monthly USD list prices: Starter59, Growth149, Scale379, Enterprise
custom. The canonical catalog and marketing comparison are synchronized.
PayU Live credentials are configured locally. Both non-chargeable Live API
probes returned HTTP200: nonexistent-transaction verification and checkout
metadata. Enabled payment-option families were returned; this does not establish
recurring or international currency capabilities.

Full PayU checkout, durable financial callbacks, subscription lifecycle,
commercial entitlements, numeric quota approval, real recurring acceptance and
restricted live-payment acceptance remain unfinished. The owner has now asked
for live checkout for personal acceptance; implementing that flow has priority.
No real payment has been initiated and no false paid access has been granted.
The request to enable it must not be represented as successful implementation.

See`PLANEBYTE_PAYU_INTEGRATION_STATUS.md` for exact provider-contract gaps and
the existing published-policy discrepancies. Two independent human reviewers and
an adjudicator are still needed for the approved120-case AI evaluation.

Current verdict: **NO-GO for commercial payments**. Product-only limited release
is pending its staged/production checks. No public signup or prospect sending.


## Approved pilot update in progress

Prices and numeric pilot allocations are approved, catalog2026-11-14.2. Monthly
commercial accounting and PayU dated verification are implemented; broader frozen
regressions and fresh production-backup recovery are running. No production
migration, new PayU mandate, real charge or public checkout is claimed here.
The public recurring launch remains blocked on merchant-specific PayU capabilities
and genuine lifecycle acceptance. Independent non-payment deployment continues.
