# PlaneByte performance before and after

Production baseline (source `0077fe32d1a0dc8b36daec38be03d0d89980c452`) used two authenticated samples: overview median20.8905s/max24.18s; source health8.2605s; opportunities8.7365s; saved13.055s/max16.793s. These are diagnostic observations, not population p95.

The staged first fix `cda3249b4fcdf8319b061660f878e4545c08c5ac` passed read/count acceptance but exposed async handlers blocking unrelated requests during synchronous database work. Mixed C2 observations reached summary median11.0445s and observed p9516.6962s. It was therefore not promoted.

The second fix moves synchronous preparation/reads off the HTTP event loop and reduces the overview summary to two database statements. Regression tests prove unrelated HTTP responsiveness while a count read is blocked and PostgreSQL summary equivalence/retention/workspace scope. The frozen full suite passes1,065 cases.

Existing PostgreSQL is Neon us-east-2; API is asia-south1. Direct database measurements showed SELECT1 median.3014s and a count plan execution.053ms. Pipelining transaction setup reduced a ten-pair diagnostic median from1.2275s to.87055s. No region, subscription or infrastructure change was made.

The UI now exposes the command entry before overview data returns, progressively renders actual summary before recent evidence, and moves advanced detail behind contextual controls. This does not by itself prove backend speed. New exact-release concurrency and production browser measurements remain required before claiming the 2s p95 target.
