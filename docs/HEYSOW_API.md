# HeySow API — current internal contracts

This application currently uses an authenticated frontend/backend gateway, not a
public customer API. Customer API keys, scopes, public developer documentation,
webhooks and MCP authentication are not implemented. Do not distribute the
gateway signing secret or describe it as a customer API credential.

The browser calls the existing authenticated Next backend-for-frontend, which
signs requests to FastAPI. The backend verifies actor, timestamp, unique nonce,
method, raw path/query and body signature. Workspace authority is resolved from
active membership; browser-selected resource IDs never establish ownership.

## Gated foundation contracts

The following require `HEYSOW_WORKSPACE_MANAGEMENT_ENABLED=true` in an isolated
runtime. Its default is false; no deployed value was changed. Unsupported feature
requests return 503 rather than creating fake account/workspace records.

| Endpoint | Authority and behavior |
|---|---|
| GET /api/organization/workspaces | Signed account's active memberships and validated selection |
| PUT /api/organization/active | UUID target; active target membership required; updates personal preference |
| POST /api/organization/workspaces | Company name and request UUID; server supplies owner; account-scoped idempotency |
| GET /api/profile | Signed account's personal profile only |
| PUT /api/profile | Validated personal fields and version; email/actor/workspace are not writable |
| GET /api/organization/profile | Current organization's company information and version |
| PUT /api/organization/profile | Owner/admin; exact version required; provenance and audit recorded |
| GET /api/organization/invitations | Owner/admin; paginated states without token/digest |
| POST /api/organization/invitations | Owner/admin; allowed role; one-time private capability response |
| DELETE /api/organization/invitations/{id} | Scoped manager revocation; ID alone grants no authority |
| POST /api/organization/invitations/respond | Named signed recipient plus capability and ACCEPT/REJECT |
| GET /api/organization/notifications | Current member's notifications for the current workspace only |
| GET/PUT /api/organization/onboarding | Resumable reviewed setup; owner/admin writes with exact revision |
| POST /api/organization/onboarding/complete | Validates persisted profile, objectives, services, owned ACTIVE ICP and preferences; no scan/send |
| GET/POST /api/organization/domains | Scoped history or one-time DNS TXT challenge; digest stored, never returned in history |
| POST /api/organization/domains/{id}/verify | Bounded DNS check with persisted cooldown/attempt reservation and post-I/O authority recheck |
| DELETE /api/organization/domains/{id} | Revokes proof while retaining historical evidence |
| POST /api/organization/website-reviews | Additional default-off discovery gate; idempotent bounded asynchronous review job |
| GET /api/organization/website-reviews/{id} | Owned job status and literal extracted proposals, never ownership verification |
| POST /api/organization/website-reviews/{id}/control | Owned cancellation or bounded retry |
| POST /api/organization/website-reviews/{id}/confirm | Explicit reviewed selected fields with profile conflict protection and provenance |
| GET /api/organization/icps/ai-status | Safe capability/budget status; no provider call |
| POST /api/organization/icps/interpret | Additional default-off AI gate; bounded editable inactive draft, never automatic persistence/discovery |

New request bodies reject extra fields. Typed response schemas constrain identity,
role, status, UUID and profile values. Concurrent personal/company edits use
opaque versions and return 409 without replacing the latest saved profile.
Raw invitation capabilities are returned only on creation with no-store caching.
Do not put tokens into query strings or log request/response bodies for those APIs.

Account creation is not one of these contracts. A permitted Google account can
create a workspace, but public registration and domain-matching membership remain
unavailable. New workspaces remain onboarding-incomplete and cannot access product
APIs merely because they have an owner.

## Existing source API isolation

Acquisition settings now read/write only the current workspace's enabled sources
and bounded budgets. Platform provider/copy state remains separate. AI plan-cache
keys and new rows include organization and actor. Repeated requests in another
workspace cannot reuse the first workspace's private result.

Existing platform provider tests, Sheets OAuth/import connections and global
controls are restricted to the internal workspace. Domain/worker guards also
prevent adoption of the internal connection/copy service. A customer's settings
never represent those credentials as a connected customer integration. A genuine
workspace integration model is required before those capabilities can be exposed.

## Release constraints

All current evidence is isolated development verification. Public API admission,
per-key capabilities/rate limits, credential hashing/rotation/revocation, webhook
signatures, developer UX and independent API acceptance remain future milestones.
PostgreSQL-specific migrations/concurrency/restore also require staging validation.
