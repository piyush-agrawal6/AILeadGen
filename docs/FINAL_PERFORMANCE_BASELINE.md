# Final performance baseline — November 14

Current API: `leadengine-api-00138-suf`. Starting source `e8ff078dc356653873d2f26de4d0563dd3ff7096`.
Production database was read from the actual API Secret Manager reference, not assumed from `.env`.
Provider: **Neon**, transaction-pooler hostname: **True**;
PostgreSQL **18.7 (a21afb5)**, schema **46**, encoding **UTF8**.
Runtime credential equals the root configuration (presence/equality only; no credential is logged).

Cloud Run: **asia-south1**; database provider region: **us-east-2**.
Initial connection: **1.9909s**. Eight sequential `SELECT 1` reads on one
connection: median **0.3014s**, maximum **0.6607s**. The real scoped signal-count
query's database execution time was **0.053ms**.
This demonstrates material network/round-trip overhead, not a slow count-query plan.
No infrastructure movement, upgrade or provider budget change is authorized by this measurement.

Existing production two-sample baseline: overview20.891s median, source health8.261s,
opportunities8.737s, saved13.055s. Such small samples are diagnostic, not a population
p95 or scalability certification. Warm/cold and concurrency measurements are required.

Priorities: eliminate repeated context/session and preview-list round trips, provide
small summary reads, remove browser capability waterfalls, keep source/provider work
out of ordinary reads. Never cache permission decisions across requests/provider waits.

Evidence: `data/artifacts/verification/final-remediation/production-checkpoint.json`,
`signal-count-plan-private.json`, and prior `final-product/production-after.json`.
