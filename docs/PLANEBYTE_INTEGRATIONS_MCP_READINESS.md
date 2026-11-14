# Integrations and MCP readiness

Existing shared MCP transport: `/api/v1/mcp` on the approved backend origin.
Authentication uses an expiring, hash-stored scoped bearer key. Read-only Intent
Radar clients need `mcp:use` and `intent:read`, current member access, completed
onboarding, enabled developer/MCP gates and an enabled workspace product grant.
Never infer a client connection from an available provider card.

The existing key issuance, rotation and revocation pages remain the source of
credential administration. Keys are shown once. Do not paste them into prompts,
URLs, documentation examples, screenshots or browser local storage. Each request
rechecks scope, expiry, membership and availability. Disabled Lead Engine tools
are omitted and direct calls remain blocked, with source implementations intact.

## Acceptance requirements

1. Issue an explicitly scoped controlled acceptance credential.
2. Use a real compatible Streamable HTTP client to initialize, list tools and
   read authorized monitors/signals; do not use a fake connection flag.
3. Check wrong-workspace, insufficient-scope, expiry and revocation failures.
4. Verify the API/MCP usage ledger and no quota bypass.
5. Revoke the acceptance credential and verify denial again.
6. Record exact endpoint, client/version and result. A library/protocol fixture
   pass is separate from external ChatGPT, Claude or VS Code compatibility.

No additional customer Slack/CRM/provider authorization is advertised as active.
Source cards describe bounded source adapters, not personal account connections.
HN uses its official public API; optional Stack Exchange and reviewed RSS/Discourse
sources retain their existing licensing and SSRF/configuration gates. No third-
party terms are accepted or hosts enabled automatically by this release.

The integration details now expose the configured public backend endpoint and
copy a native Copilot `mcpServers` configuration with explicitly selected read
tools and a `${PLANEBYTE_MCP_KEY}` environment reference. No real key is copied
into the JSON. The current [official configuration reference](https://code.visualstudio.com/docs/agents/reference/mcp-configuration)
distinguishes this portable format from deprecated editor `servers`/`inputs`
configuration. Syntax support is not proof of a connected named client.
Production MCP acceptance remains to be verified.
