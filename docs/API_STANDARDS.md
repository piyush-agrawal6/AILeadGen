# API standards

Retain the existing signed gateway and Pydantic boundaries. New APIs require authenticated membership, resource scope, permission/module checks, bounded inputs and pagination, consistent safe errors and tests. New breaking contracts should be versioned; existing routes are not renamed blindly.

Template PUT now requires an existing owned record; conflict updates cannot transfer ownership. Legacy experiment endpoints return404 by default. OAuth route exemption is exact `/api/auth` or `/api/auth/…`, not an arbitrary shared prefix.

Do not return credentials, arbitrary provider errors or database rows that have not been scoped. Idempotency remains required for discovery, campaign execution and send writes. Scoped API/MCP and signed webhooks are now implemented and tested locally; public production activation and external acceptance remain pending. See the Phase 1–6 tracker for current evidence.
