# PlaneByte production release — 2026-11-13

**LIMITED GO — the owner-only production release is live.** Genuine backend,
source, AI, scheduled-worker and MCP acceptance passed. Browser acceptance is
reserved for the owner, who explicitly requested that browser testing stop.
This is not a certification of unrestricted signup, every optional integration,
AI accuracy, commercial licensing, load capacity or a full customer journey.

## A. What was fixed

- Published the repaired source history without force-pushing shared history.
  Generated Next caches, backups, credentials and validation artifacts were
  excluded. All preexisting source changes were preserved.
- Connected the existing Vercel `leadengine` project to
  `piyush-agrawal6/AILeadGen`, production branch `main`, root `dashboard`, Node 24.
  Latest source was built by that actual GitHub integration and promoted normally.
- Configured the only allowed login as `planebyte@gmail.com` on frontend/backend.
  Public signup, invitation admission and other admitted-customer access remain
  off. Existing Google OAuth/session/gateway credentials were retained.
- Added Google's explicit account chooser. The existing verified-email allowlist,
  PKCE, secure session cookies and server-side membership checks remain intact.
- Removed idle middleware database connections before downstream handlers obtain
  their own connections, while retaining the verified request workspace context.
- Corrected the database probe: PostgreSQL startup options caused the earlier
  diagnostic timeout. Standard connections and explicit read-only transactions
  work; the earlier result was not a confirmed database outage.
- Recovery-tested the additive schema 15 → 44 upgrade, then applied its 29 pending
  migrations once in production. Resumed rollout detected schema 44 and applied
  zero additional migrations. No reset, truncation or broad deletion occurred.
- Verified the existing legacy owner's ADMIN identity, then the actual persisted
  backfilled PlaneByte OWNER membership, completed onboarding and product rows.
  Granted Beta only to that verified workspace, with an idempotent audit record.
- Deployed the existing API, worker, acquisition and canary resources, preserving
  their identities and unrelated Gmail/storage/provider settings. Preserved the
  acquisition worker's actual Python module entrypoint.
- Fixed a rollout failure caused by trying to replace a secret-backed allowlist
  with a literal: retained its secret-backed type and set its authorized value.
- Published the existing valid integration encryption key through server-only
  Secret Manager access for the existing identities. No JSON service-account key
  or replacement AI integration was created.
- Restored inbox synchronization after maintenance and installed the missing
  Radar dispatcher against the existing worker and existing service identity.
- Removed a real credential from an uncommitted example environment edit. The
  server credential was preserved; no credential value was committed or printed
  in the release audits.
- Reverted all dashboard Cloud Run source changes introduced during an incorrect
  hosting interpretation and removed the unused image. No dashboard Cloud Run
  service, load balancer, DNS change or marketing-site change was created.

## B. What is live

| Component | Verified production state |
|---|---|
| SaaS | https://app.planebyte.com — existing Vercel project; new release promoted |
| Frontend source | `4c43940fd2cc3ed4e697ff524a443328719ba85a` |
| Vercel deployment | `dpl_Ac9v2oMHRqZ3W8P9Dgb5AFLu9YHc`, READY; https://leadengine-qkoriha40-piyushagrawal6s-projects.vercel.app |
| Backend | https://leadengine-api-befca7xg4a-el.a.run.app |
| Backend revision/image | `leadengine-api-00118-yok`; `api:beta-20261113-r2` in existing Artifact Registry |
| Workers | Existing `leadengine-worker`, `leadengine-acquisition`, `leadengine-quota-canary`; `worker:beta-20261113-r1` |
| Database | Existing Neon PostgreSQL 18.6; schema 44; retained original customer/history data |
| Authentication | Owner-only policy deployed; approved-owner browser session not independently completed |
| Lead Engine | Product available to the owner; signed workspace/product/safety reads pass; local workflow regressions pass |
| Intent Radar | Stage `Beta`; enabled only for the verified PlaneByte workspace below |
| Vertex | Real API service-identity structured inference HEALTHY; real signal interpretation persisted as `VERTEX_AI`, `gemini-3.6-flash` |
| Hacker News | Real bounded production discovery COMPLETED; genuine signal saved and opportunity created |
| Monitoring | Actual Google Scheduler → existing worker → scheduled discovery COMPLETED; saved six-hour policy retained |
| MCP | Official client handshake passes; 18 tools discovered; permitted Radar read passes; temporary key revoked and rejected with 401 |
| Gmail | Existing account CONNECTED; SMTP READY, IMAP READY; inbox sync enabled; sending disabled |
| Other Radar sources | Stack Exchange requires approval; RSS/Atom/Discourse require approved configured publisher endpoints |
| Marketing | Existing Netlify site unchanged |

Verified workspace: `e5ffc3dc-241e-5558-acd4-84f5fe354ca7`, stored name PlaneByte,
active OWNER `planebyte@gmail.com`, completed onboarding. No other active member
or workspace received a Beta grant.

The existing Vercel team remains Hobby. Vercel accepted both the production build
and promotion. The owner explicitly directed continued use of that project and
no subscription changes; billing was not treated as a technical deployment error.
No subscription was changed or hosting migration performed.

## C. Safety and preservation

- Fresh restricted PostgreSQL custom backup was restored into private local
  PostgreSQL 18. Every original row/column across 91 original tables matched after
  migration, allowing only the documented legacy workspace-ID backfill.
- Maintenance-window backup SHA-256:
  `085d4db6fe55685f4990ff2f7c04bf96f568d2706d483d479154b37bad6ff5bc`.
  Backup/recovery/config snapshots remain private under `data/backups/`.
- Final production counts: prospects 7; contacted recipients 34; permanent send
  records 44; email messages 2; pipeline runs 5. Suppression table/history retained.
  **Zero outbound messages were sent during this release.**
- `AUTO_SCAN_ENABLED=false`, `AUTO_EMAIL_ENABLED=false`,
  `EMAIL_SENDING_ENABLED=false`; customer live sending and public admission off.
- Outreach/acquisition schedulers remain paused. Inbox sync is enabled every five
  minutes. The separate Radar dispatcher is enabled every ten minutes; each saved
  monitor remains subject to its actual minimum six-hour schedule and usage caps.
- Controlled recurring acceptance advanced only its named monitor's next due
  timestamp, with a scoped audit record. The actual worker completed job
  `82052719-e751-4c22-a8b1-884bf4c69385`; next run was persisted for
  `2026-11-13T16:19:38.665002+00:00` (21:49 Asia/Kolkata). This was an expedited
  due-time test, not a claim that six hours elapsed during acceptance.
- No prospect acquisition, active vulnerability testing, real outreach, new
  customer admission or deletion was performed. The Radar test collected public
  discussions, not contactable prospect records.
- Vercel sensitive values are intentionally non-readable. Their presence and
  successful policy writes were verified without claiming list responses reveal
  their values. Automatic review rejected declassifying them; that action was
  not executed. Sensitive storage remained unchanged.

## D. Tests and actual failures

Private evidence directory: `data/artifacts/verification/beta-activation-20261113/`.

| Verification | Actual result |
|---|---|
| Full exact-lock backend + PostgreSQL 18 | 922 passed, 1 intentional live-email skip, 7 warnings |
| Connection-fix security/workspace/PostgreSQL/recovery subset | 112 passed, 2 warnings |
| Final release-policy/owner grant/probe units | 9 passed |
| Frontend units before final chooser-only change | 143 passed |
| Final auth policy/UI units | 25 passed; TypeScript passed |
| Final account-chooser/OAuth handoff browser fixtures | 3 passed; not a real owner Google login |
| Supported Node 24 optimized build | Local build passed; actual GitHub/Vercel production builds READY |
| Lint | 0 errors, 12 warnings |
| Radar phase 2/3 browser | 1 passed |
| Radar product browser | 4 passed |
| Lead Engine workflow browser | 29 passed |
| Developer/MCP/webhook browser fixtures | 2 passed |
| Gmail lifecycle/safety browser fixtures | 2 passed; no actual send |
| Recovery | Exact restore, 29 additive migrations, second run zero, no original row/column loss |
| Live security | Anonymous protected pages redirect to login; signed unapproved API actor denied 401; sending false |
| Live AI | Attached API identity structured inference and persisted Radar interpretation passed; no fallback used |
| Live source | One bounded five-item HN collection completed and returned genuine matching evidence |
| Live MCP | Handshake/read passed, temporary credential revoked, subsequent request 401 |
| Live scheduler | Real scheduled job COMPLETED, future due time and history persisted |
| Owner browser acceptance | Delegated to the owner at their explicit request; not claimed complete |

Historical failures were retained rather than suppressed: initial backup timeout
(corrected bounded allowance); PostgreSQL 16 dump tool against server 18 (matching
18 tools fixed it); secret/literal allowlist type mismatch (fixed preserving the
secret-backed type); initial 20-second capability probe timeout (longer diagnostic
succeeded, followed by the verified connection-lifetime fix). Observed authenticated
responses can still take several seconds across current regions; no scale/SLA or
load-capacity claim is made.

Preview deployments lack separate preview environment secrets and have failed
configuration checks. Production-target deployments use the existing production
secrets and are READY. Production secrets were not copied into arbitrary preview
branches to hide those preview failures.

## E. GitHub and deployment

- Release branch: `codex/production-beta-20261113`; intended remote:
  https://github.com/piyush-agrawal6/AILeadGen.
- Source/history recovery `601f6c4` preserved remote ancestor `03398f6`; no force
  push. Source release `cb23a1a`; architecture correction `dc3e510`; guarded rollout
  `9b92d37`; connection fix `a06729c`; final frontend account chooser `4c43940`.
- Main received and Vercel built exact frontend commit
  `4c43940fd2cc3ed4e697ff524a443328719ba85a` through the GitHub integration.
- Production domain assignment was verified using Vercel's actual alias API,
  independently of deployment READY status. Explicit promotion remains enabled
  as the release procedure; no DNS changes were needed.
- API/worker release build `03a25369-aeae-463c-8b48-9d30328442f5`; focused API build
  `34440ea0-a9b2-4b3e-8c47-b7463bd323d7`; both succeeded with pinned runtime checks.
- Runtime identities were preserved. Frontend uses Node 24 on Vercel; backend/jobs
  use Python 3.12 and the current lock on the existing Google Cloud project.

## F. Exact remaining owner actions / limitations

1. Open https://app.planebyte.com and select **planebyte@gmail.com** in the Google
   account chooser. The previous browser attempt returned AccessDenied without
   recording the selected account's identity. Do not assume that proves the
   approved owner succeeded or failed. Browser testing is now owner-controlled.
2. Additional source activation requires exact publisher-approved endpoints,
   policy/attribution/retention scope and, for Stack Exchange, approved commercial
   site scope. This does not block the active HN-only beta.
3. Independent AI quality/calibration and reviewed currency pricing remain
   unverified. Scores are evidence-backed interpretations, not calibrated buying
   probabilities. Monetary estimates stay unknown without approved pricing.

No missing secret is currently requested. No Pro upgrade, alternate frontend host,
public signup or live sending is part of this release. Full browser acceptance and
optional source/quality certification remain unclaimed.
