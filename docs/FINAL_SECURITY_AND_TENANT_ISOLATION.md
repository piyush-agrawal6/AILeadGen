# Security and tenant isolation

The current full isolated backend suite passes1065 tests, including PostgreSQL, absent/cross-workspace denial, current membership/role/module guards, signed worker context, key expiry/revocation, source SSRF fences and retention checks. No permission decision was cached or relaxed to fix old tests. Backend context is freshly verified per request; asynchronous offload copies only the already verified identity context and closes preparation connections.

The graph uses version-checked existing organization profile/preferences endpoints and workspace-bound graph query keys. Signal drawers reuse existing authorized detail/mutation paths. Private assistant keys include actor/workspace, and stored conversations remain server-authorized. Frontend navigation is not an authorization boundary.

Google authentication and existing owner allowlist stay unchanged. Public registration, Lead Engine availability, automatic scans/email and sending remain closed. Secret values are never included in audit output, browser assets or source commits. No .env/OAuth change or production reset/delete is part of this release.

Backup/restore was tested locally against fresh production backup with exact original row fingerprints and zero loss. Production schema46 remains unchanged. Preserved Lead Engine/contact/suppression history must be rechecked after any rollout. The test result is not a claim of completed penetration testing, named-provider certification or public SaaS readiness.
