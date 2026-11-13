# PlaneByte production environment and activation requirements

Release execution resumed from HEAD `f9350a8`, remote main `03398f6`. Values below are contracts, never secrets. Existing environment values, OAuth credentials and active `leads.planebyte.com` callbacks remain intact. A modified `.env.example` is owner work and is not evidence that production is configured.

## Confirmed account/deployment blockers

- Vercel account is authenticated. Current team `piyushagrawal6s-projects` is **Hobby**, not eligible for this commercial deployment. Owner must upgrade/assign an eligible team before commercial activation. Actual project is **leadengine**, not historical `planebyte`.
- Existing Google Cloud project `querryside` has reachable `leadengine-api` at `https://leadengine-api-befca7xg4a-el.a.run.app`; HTTP health is successful. Existing worker/acquisition jobs remain preserved. No dedicated Radar recurring-dispatch scheduler was listed. Source/AI/DB/MCP runtime acceptance is not established by health.
- `app.planebyte.com` is assigned and verified on existing Vercel project `leadengine`; HTTPS returns 307 to `/login`. OAuth registration remains unverified. No app DNS change is currently required. Preserve the existing Netlify root site and business-email DNS.
- Owner-approved beta workspace IDs/product grants and publisher-specific commercial approvals have not been supplied. No unapproved source is activated.
- Independent AI reviewer labels, owner-approved thresholds, supported-language scope and pricing inputs remain required for quality/cost release acceptance.

## Exact activation contracts

| Variable | Required value type / accepted format | Runtime / sensitive | Current verification / blocker | Apply |
|---|---|---|---|---|
| `INTENT_RADAR_STAGE` | `Disabled`, `Internal Preview`, or `Beta` (exact enum) | Backend/worker; no | Presence-only inspection and deployed configuration verification required. Beta still requires persisted workspace grants and completed onboarding. | Restart/authorized rollout |
| `INTENT_RADAR_INTERNAL_WORKSPACES` | Comma-separated approved organization IDs; used for `Internal Preview` | Backend/worker; private IDs | Exact approved workspace IDs required. Never substitute client-supplied IDs for membership. | Restart/rollout |
| `INTENT_RADAR_STACKEXCHANGE_ENABLED` | Boolean; activation after terms approval | Backend/worker; no | Commercial API/CC BY-SA acceptance required; successful bounded transport is separate. | Restart/rollout |
| `INTENT_RADAR_STACKEXCHANGE_KEY` | Optional Stack Apps application key | Backend/worker; **secret** | Optional quota key; obtain at Stack Apps. No customer OAuth account assumed. | Restart/rollout |
| `INTENT_RADAR_STACKEXCHANGE_SITES` | Semicolon-separated approved site API names | Backend/worker; no | Sites must be allowlisted; per-search selects at most three. | Restart/rollout |
| `INTENT_RADAR_APPROVED_FEED_HOSTS` | Semicolon-separated exact public HTTPS hostnames; no wildcard | Backend/worker; no | Approved RSS/Atom/Discourse endpoints and terms/retention references required; workspace feed configs separately persisted. | Restart/rollout, then reviewed API config |
| `INTENT_RADAR_SCHEDULES_ENABLED` | Boolean, explicit opt-in | Backend/worker; no | Real independent worker/scheduler dispatch and paused/revoked guards required. | Restart/rollout |
| `INTENT_RADAR_MIN_SCHEDULE_HOURS` | Positive interval policy; current supported frequencies 6/12/24 hours | Backend/worker; no | This is the actual source contract. Do not silently use historical `INTENT_RADAR_MIN_SCHEDULE_HOURS`/other spelling without source validation. | Restart/rollout |
| `INTENT_RADAR_AI_ENABLED` | Boolean, explicit approval | Backend/worker; no | Genuine Vertex runtime acceptance and bounded workspace preferences still required. | Restart/rollout |
| `INTENT_RADAR_AI_DAILY_CALLS`, `INTENT_RADAR_AI_DAILY_TOKENS` | Positive integers; 50/100000 are owner proposed caps, not authorization to exceed workspace preferences | Backend/worker; no | Analysis checks minimum of operator limit and saved workspace limit; shared global feature reservations also apply. | Restart/rollout |
| `HEYSOW_DEVELOPER_API_ENABLED`, `HEYSOW_MCP_ENABLED` | Booleans | Backend; no | Existing hashed expiring workspace developer keys and `mcp:use` + `intent:read` scopes required. | Restart/rollout |
| `MCP_ALLOWED_HOSTS`, `MCP_ALLOWED_ORIGINS` | Exact verified host/origin lists in source parser format; no wildcard | Backend; no | Verified deployed MCP host and approved client HTTPS origins required. Do not derive wildcard origins from catalog logos. | Restart/rollout |
| `AI_PRIMARY_PROVIDER`, `AI_PROVIDER` | Existing compatible `vertex`/`gemini` selectors | Backend/worker; no | Existing Vertex-first router; no duplicate framework. | Restart/rollout |
| `VERTEX_AI_ENABLED`, `VERTEX_AI_PROJECT_ID`, `VERTEX_AI_LOCATION`, `VERTEX_AI_MODEL` | Boolean + approved project/location + actually available model ID | Backend/worker; project private, no key | Existing attached service identity, Vertex API/IAM/billing/model acceptance required. Prior local model success is not deployed acceptance. | Restart/rollout |
| `GEMINI_API_ENABLED`, `AI_FALLBACK_ENABLED`, `GEMINI_API_KEY`, `GEMINI_MODEL` | Approved optional fallback bool/model/key | Backend/worker; key **secret** | Existing compatibility validation; fallback may remain unavailable honestly, not fake success. | Restart/rollout |
| `AUTH_SECRET`, `AUTH_GOOGLE_ID`, `AUTH_GOOGLE_SECRET` | Existing session secret and Google web-client credentials | Vercel/backend; **secrets** | Preserve existing credentials. Verify callbacks for actual assigned app domain and active legacy host. | Vercel redeploy/backend restart |
| `AUTH_URL`, `LEADENGINE_API_URL` | Verified canonical SaaS HTTPS origin / actual private server API URL | Vercel server; no | Domain assignment and real backend signed request acceptance required. | Vercel redeploy |
| `LEADENGINE_API_SIGNING_SECRET` | Existing matching HMAC secret at Vercel/backend | Both; **secret** | Matching values verified without output; never public env variables. | Both restart/redeploy |
| `DATABASE_BACKEND`, `DATABASE_URL` | Production `postgres` + managed PostgreSQL connection/identity | Backend/worker; URL **secret** | Fresh/additive staging migrations, backup/restore, durable connectivity/pooling required. Never activate SQLite production. | Approved migrations and restart |
| `ALLOWED_USER_EMAILS` | Existing approved account allowlist; source parsing preserved | Vercel/backend; private | Public signup remains blocked. No test account/password workaround in production. | Restart/redeploy |

Full presence-only local inventory is reproducible with `scripts/intent_radar_release_inventory.py`; deployed inventory with `scripts/inspect_planebyte_deployment.py`. No secret value is emitted. Existing nonempty values are preserved. Presence does not establish a valid identity, matching secret or completed callback acceptance.

## Current presence / generation / runtime inventory (2026-11-11)

`L` = root `.env`; `V` = Vercel production; `B` = Cloud Run API. Worker values must be separately verified. Vercel has **no preview-target environment entries**. All changes below require the owning runtime's restart/redeploy; no activation or secret mutation has been performed.

| Variable | Presence | Type / generate or obtain at | Runtime | Sensitive | Missing / blocking | Actual verification |
|---|---|---|---|---|---|---|
| `INTENT_RADAR_STAGE` | L absent; B absent | Exact enum `Disabled`, `Internal Preview`, `Beta`; owner release decision | B/worker | No | Yes / activation | Defaults Disabled; no unrestricted stage exists |
| `INTENT_RADAR_INTERNAL_WORKSPACES` | L absent; B absent | Comma-separated exact approved org IDs; owner workspace registry | B/worker | Private IDs | Yes / preview gate | Used only for Internal Preview; Beta still requires stored product grants |
| `INTENT_RADAR_STACKEXCHANGE_ENABLED` | L present; B absent | Boolean; owner commercial approval | B/worker | No | Yes / SE activation | Terms fetch403; alternate documentation404; no approval inferred |
| `INTENT_RADAR_STACKEXCHANGE_KEY` | L present; B absent | Optional Stack Apps application key | B/worker | Yes | Production missing / not intrinsically required | Optional key is server-only; local presence not commercial permission |
| `INTENT_RADAR_STACKEXCHANGE_SITES` | L absent; B absent | Semicolon-separated approved API site names | B/worker | No | Yes / scope approval | Default `stackoverflow;softwareengineering;webmasters` is code, not owner approval |
| `INTENT_RADAR_APPROVED_FEED_HOSTS` | L absent; B absent | Semicolon-separated exact approved hostnames | B/worker | No | Yes / feed activation | No wildcard; public pinned DNS required; feed IDs/terms/retention separately stored |
| `INTENT_RADAR_SCHEDULES_ENABLED` | L present; B absent | Boolean opt-in; owner | B/worker | No | Yes / recurring activation | Independent worker mode `LEADENGINE_AUTOMATION_MODE=intent-radar-dispatch` now implemented; deployed scheduler absent |
| `INTENT_RADAR_MIN_SCHEDULE_HOURS` | L present; B absent | Integer 6–24; permitted policy | B/worker | No | Production missing / schedules | Actual schedule frequencies 6/12/24 hours checked against policy |
| `INTENT_RADAR_AI_ENABLED` | L present; B absent | Boolean; owner | B/worker | No | Yes / AI activation | Local real Vertex accepted; deployed Radar AI not accepted |
| `INTENT_RADAR_AI_DAILY_CALLS` | L present; B absent | Integer 1–50; requested operator cap50 | B/worker | No | Production missing / costs | Minimum of operator and saved workspace limit; defaults bounded |
| `INTENT_RADAR_AI_DAILY_TOKENS` | L present; B absent | Integer 6000–300000; requested operator cap100000 | B/worker | No | Production missing / costs | Workspace-scoped committed upper-bound reservations, including drafts; not billed tokens |
| `HEYSOW_DEVELOPER_API_ENABLED` | L present; V/B absent | Boolean; owner | V/B | No | Yes / external API | Scoped keys/expiration/revocation remain required |
| `HEYSOW_MCP_ENABLED` | L present; B absent | Boolean; owner | B | No | Yes / MCP | Nine real read-only tools; SDK acceptance is isolated, not deployed-client acceptance |
| `MCP_ALLOWED_HOSTS` | L present; B absent | Comma-separated exact hostnames, optional port | B | No | Yes / MCP | Verified backend host `leadengine-api-befca7xg4a-el.a.run.app`; production wildcards rejected |
| `MCP_ALLOWED_ORIGINS` | L present; B absent | Comma-separated exact HTTPS origins | B | No | Yes / MCP | SaaS origin verified `https://app.planebyte.com`; other origins require actual client approval |
| `AI_PRIMARY_PROVIDER` | L/B present | Exact `vertex` or `gemini`; owner policy | B/worker | No | No / deployed inference pending | Existing gateway preserved; local primary Vertex successful |
| `AI_PROVIDER` | B present; L compatibility contract | `vertex` or `gemini`; existing compatibility selector | B/worker | No | No / compatibility check | No second framework |
| `VERTEX_AI_ENABLED` | L/B present | Boolean; owner | B/worker | No | No / deployed acceptance pending | Existing identity/config retained |
| `VERTEX_AI_PROJECT_ID` | L/B present | Existing authorized GCP project | B/worker | Private ID | No / IAM acceptance pending | Existing `querryside` preserved |
| `VERTEX_AI_LOCATION` | L/B present | Available approved Vertex region | B/worker | No | No / deployed acceptance pending | Local configured region accepted; no model/region guessed |
| `VERTEX_AI_MODEL` | L/B present | Verified available model identifier | B/worker | No | No / deployed acceptance pending | Local `gemini-3.6-flash` actually returned inference; production identity not thereby accepted |
| `GEMINI_API_ENABLED` | L/B present | Boolean optional fallback policy | B/worker | No | No / fallback approval pending | Existing behavior retained; local Vertex probe used no fallback |
| `AI_FALLBACK_ENABLED` | L/B present | Boolean owner-approved fallback | B/worker | No | No / acceptance pending | Radar now bounds attempts separately while Lead Engine defaults retained |
| `GEMINI_API_KEY` | L/B present | Existing Gemini API key/secret manager | B/worker | Yes | No / deployed validation pending | Never copied to frontend or printed |
| `GEMINI_MODEL` | L/B present | Available approved Gemini identifier | B/worker | No | No / fallback model check pending | No invented identifier or fallback success |
| `AUTH_SECRET` | L/V present | Existing cryptographically random session secret | V | Yes | No / login acceptance pending | Preserve; preview-target entry absent |
| `AUTH_URL` | L/V absent | Verified canonical HTTPS SaaS origin | V | No | Yes / canonical callback review | Auth.js automatic host behavior is not OAuth console verification |
| `AUTH_GOOGLE_ID` | L/V/B present | Existing Google OAuth web client | V/B | Server-only config | No / callbacks pending | Exact app callback registration must be verified |
| `AUTH_GOOGLE_SECRET` | L/V/B present | Existing OAuth secret manager | V/B | Yes | No / callbacks pending | Existing legitimate Gmail/Sheets legacy callbacks preserved |
| `LEADENGINE_API_SIGNING_SECRET` | L/V/B present | Existing matching HMAC secret | V/B | Yes | No / matching values pending | Presence checked without value disclosure; no production test bypass |
| `LEADENGINE_API_URL` | V/dashboard local present | Verified backend HTTPS origin | V server | No | Preview missing / preview blocker | `/api/health`200; signed customer journey still pending |
| `DATABASE_BACKEND` | L/B absent | Explicit production `postgres`; owner runtime | B/worker | No | Configuration review / DB blocker | Actual source selects PostgreSQL from valid DATABASE_URL; SQLite not accepted for release |
| `DATABASE_URL` | L/B present | Existing managed PostgreSQL identity/secret | B/worker | Yes | No / staging and recovery pending | 58 isolated PostgreSQL checks pass; not production DB acceptance |
| `ALLOWED_USER_EMAILS` | L/V/B present | Owner-approved account list | V/B | Private list | No / actual beta account pending | No public signup enabled |
| `HEYSOW_INTEGRATION_ENCRYPTION_KEY` | L present; B absent | Existing server integration encryption key | B/worker | Yes | Yes / shared secure integration activation | Preserve existing Gmail behavior; no new unsafe key or plaintext fallback |
| `AI_MODEL_PRICING_JSON` | L/B absent | Operator-reviewed per-model USD/million-token pricing with HTTPS reference and `approved:true` | B/worker | No | Yes / currency estimates | Provider tokens real; currency remains unknown without reviewed pricing |
| `LEADENGINE_AUTOMATION_MODE` | Radar scheduler absent | Existing Cloud Run Job override `intent-radar-dispatch` | worker | No | Yes / scheduling | Requires valid schema, production flags, durable executor and IAM; no web-request-only scheduling claim |

No secret currently known to be absent locally must be invented. Missing production/preview configuration is distinct from missing credentials. Additional owner inputs: exact beta IDs and product grants, commercial plan/team, publisher endpoints/permissions (including a working approved Atom endpoint), Stack Exchange terms acceptance, independent corpus/reviewers/thresholds, staging PostgreSQL target and tested production backup/rollback. App DNS already verifies; OAuth callback approval remains required.
