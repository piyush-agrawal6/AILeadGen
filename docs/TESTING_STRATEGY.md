# Testing strategy

Use pytest for domain/security/migration tests, Vitest for UI state and policy tests, and Playwright for actual browser workflows. Tests use isolated local databases and dummy OAuth credentials. External acquisition, inbox sync and SMTP must stay disabled unless an owner explicitly authorizes a separate controlled acceptance.

Auth checks cover exact public routes, sanitized errors, pending/disabled states, desktop/mobile overflow, Google handoff and protected private APIs. Module tests cover default-denied legacy access and zero side effects from disabled dispatch. Template tests cover own-signature rendering without audits/PDFs and cross-tenant takeover prevention.

Retain historical tests behind explicit legacy opt-in. Do not weaken tenant checks to satisfy fixtures. Record broader baseline failures as release blockers until repaired. Migration preservation and cross-tenant integration testing are mandatory before public registration.
