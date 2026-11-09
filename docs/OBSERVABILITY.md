# Observability

Current building blocks include health routes, safe worker diagnostics, acquisition/workflow events, audit logs and read-cache counters. Retain them during cleanup. Never log credentials, auth tokens, message bodies or unnecessary personal data.

New operations should correlate request/job/workspace IDs, duration, safe error category and retry outcome. Measure provider failures, queue depth, stale leases, cache hit/miss and query latency before expanding infrastructure. Alerts must be actionable and avoid unchanged-state notification spam.

No new external monitoring service, production load test or invented uptime/latency metric was introduced. Full tracing, performance dashboards and staging capacity baselines remain unimplemented work.
