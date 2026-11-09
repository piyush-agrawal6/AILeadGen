# Background jobs

Reuse current Cloud Run/executor services, leases, source request ledgers, cancellation, concurrency limits and idempotent sends. Jobs must bind a trusted workspace, recheck authorization before sensitive operations, and expose safe status/progress/errors.

Old experiment `tick` and `can_send` now return before database/provider work when the internal experiment feature is disabled. Preparation and fixed-introduction sending are also gated. Disabling a module does not erase its historical records or resume paused jobs.

Do not retry permanent authorization/validation failures, uncertain SMTP outcomes or exhausted resources in an infinite loop. No schedules or infrastructure were changed in production during this cleanup.
