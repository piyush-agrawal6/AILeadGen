# Performance before and after

See `PLANEBYTE_PERFORMANCE_BEFORE_AFTER.md` for the measured baseline and repair rationale. The fresh isolated full suite confirms HTTP event-loop responsiveness while database work is blocked and an exactly two-statement overview summary with PostgreSQL retention/tenant equivalence. This is correctness evidence, not a production latency result.

| Observation | Source | Result |
|---|---|---|
| Production overview, two samples |0077fe3|20.8905s median,24.18s maximum|
| Production opportunities, two samples |0077fe3|8.7365s median|
| First staged summary, mixed C2, three samples |cda3249|11.0445s median,16.6962s observed p95; not promoted|
| Direct PostgreSQL SELECT1, eight samples |existing production DB|.3014s median; database and API regions differ|
| Transaction setup, ten diagnostic pairs |same connection/provider|1.2275→.87055s median with pipeline|
| Staged summary, mixed C2, three samples |b11d753|5.9926s median,10.6542s observed p95; not promoted|
| Staged full overview, same workload |b11d753|12.1874s median,16.9434s observed p95; not promoted|
| Current service implementation |unreleased continuation|Two-statement summary / three-statement full overview budgets pass isolated SQLite/PostgreSQL equivalence checks; full authenticated request latency remains unmeasured|

The new home command remains usable while actual summary/recent evidence loads; a browser regression explicitly holds the overview response and proves a typed question survives its completion. No metric is fabricated. No region/provider/subscription change is included. A2s p95 claim requires representative new-release measurements; small samples remain diagnostic.

The b11d753 trace showed a slow summary with approximately 3.6s of database time and 10.5s of application time. Inspection found synchronous scheduler maintenance on the HTTP event loop. The continuation offloads that maintenance and closes database connections before cloud dispatch. Blocking-database responsiveness tests pass; this supports the diagnosis but does not establish the size of a production improvement. Full-overview list hydration was also replaced with one bounded snapshot. Regional network latency remains a separate measured constraint.
