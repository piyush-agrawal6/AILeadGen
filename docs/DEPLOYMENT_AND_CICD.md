# Deployment and CI/CD

Use existing Vercel/Cloud Run build paths and pinned lockfiles. No DNS, credential, service-account, environment-file or production deployment change is included in this local implementation.

Release gates: lint/typecheck, unit/integration/security regressions, production build, migration preservation/restore validation, staging smoke tests and approved rollout. Do not bypass failing authorization or data-integrity tests. Keep flags default-off for archived or incomplete capabilities.

Authentication design can be reviewed locally through the auth-only Playwright configuration. It uses dummy Google client values and intercepts the OAuth destination; it never signs in to a real Google account. A public release additionally needs a complete account/onboarding backend, published legal content and verified tenant integration scope.
