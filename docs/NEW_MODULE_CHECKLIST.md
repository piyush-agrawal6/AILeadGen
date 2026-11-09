# New module checklist

Before registering a module as available:

- Define ID, version, ownership, lifecycle and dependencies.
- Reuse platform identity/workspace/permissions rather than adding another auth stack.
- Define entitlements and real usage dimensions; do not invent paid subscription state.
- Scope database, cache, files, jobs and external credentials to verified workspace context.
- Enforce permissions and module availability on APIs, workers and consequential actions.
- Bound jobs/providers and implement safe retry, cancellation, idempotency and errors.
- Use approved shared UI and meaningful empty/loading/success/error states.
- Test cross-tenant denial, direct API bypass, failures and the real user journey.
- Document settings, operational owner, migrations/rollback and measurable performance.
- Require staging/release evidence before claiming production readiness.

The registry deliberately does not advertise the planned AI Agent as enabled.
