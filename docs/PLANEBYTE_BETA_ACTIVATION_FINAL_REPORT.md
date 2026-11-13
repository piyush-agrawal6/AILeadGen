# PlaneByte beta activation — release in progress, 2026-11-13

**Current verdict: NO-GO. Production activation has not been claimed.**

The owner approved `planebyte@gmail.com` as the only permitted SaaS login and
approved Intent Radar only for their verified existing PlaneByte admin workspace.
Marketing at `https://planebyte.com` is outside this rollout and remains untouched.

## Repairs and verified diagnosis

- Preserved the earlier source-only Git history repair and all uncommitted work.
  No force push, reset, customer deletion or secret rotation.
- Removed a real provider credential from an uncommitted example environment
  file; the existing server secret was preserved. Release scans report variable
  names and paths only, never credential values.
- Corrected a PostgreSQL diagnostic: startup connection options caused the earlier
  probe timeout. Standard connections and explicit read-only transactions pass.
  This was not a confirmed production database outage.
- Added read-only runtime/provider probes and an owner-only, dry-run-first
  entitlement operation that verifies persisted membership and completed setup.
- Prepared source-only API and worker images using existing Google Cloud services,
  pinned dependencies and the existing working worker browser image.
- Restored the exact locked `cryptography==50.0.2` runtime locally; its Intel Mac
  wheel is unavailable, so the package was compiled against project-local OpenSSL.
- Updated only the authorized root access-policy settings. Production enforcement
  still requires rollout: one owner allowlist; public/invited/customer admission off.

## Actual production state last verified

| Component | Observed state |
|---|---|
| SaaS frontend | `https://app.planebyte.com`; existing Vercel `leadengine` project; November 5 deployment; redirects to login |
| Vercel plan | Existing team `piyushagrawal6s-projects` still reports Hobby; commercial upgrade pending |
| Backend | `https://leadengine-api-befca7xg4a-el.a.run.app`; revision `leadengine-api-00114-soh`; old November 5 image; liveness and signed legacy safety read pass |
| PostgreSQL | Existing Neon PostgreSQL 18.6; schema 15; latest code requires schema 44; no production migration performed |
| Workers | Existing worker/acquisition jobs preserved; no dedicated Radar dispatcher deployed |
| Google authentication | Existing credentials preserved; new release's actual owner sign-in not yet accepted |
| Lead Engine | Existing old deployment retained; latest source passes local regressions; latest live workflow pending |
| Intent Radar | Not yet activated in production; new routes absent from old backend |
| Vertex AI | Genuine local and attached worker-identity inference pass; actual new API/Radar persisted analysis pending |
| Sources | Bounded genuine Hacker News retrieval passes; additional publisher approvals/configuration unresolved |
| Recurring monitoring | Source and isolated tests exist; production scheduled-monitor acceptance pending |
| MCP | Isolated official-client tests pass; deployed authenticated handshake pending |
| Single-owner restriction | Root policy prepared; not yet claimed active on the deployed application |

Production has no organization tables yet. Its legacy owner record is
`planebyte@gmail.com` with ADMIN role. The additive migration creates/backfills the
workspace; its actual persisted ID and membership must be read and verified before
any Beta grant. No workspace grant has been made based on an assumed ID.

## Verification evidence

Artifacts are under `data/artifacts/verification/beta-activation-20261113/`.
These are local/private artifacts and must not be committed or uploaded publicly.

| Check | Actual result |
|---|---|
| Earlier full backend, PostgreSQL 16, prior installed crypto runtime | 916 passed, one intentional live-email skip, seven warnings |
| Exact locked runtime + PostgreSQL 18 full suite | Running; earlier result is not substituted for it |
| Frontend units | 143 passed |
| Supported Node 24 production build | Passed |
| Frontend lint | Zero errors, 12 warnings |
| Owner grant/runtime-probe units | Six passed before additional locking hardening; rerun pending |
| Radar phase 2/3 browser | One passed |
| Radar product browser | Four passed |
| Lead Engine workflow browser | 29 passed |
| Developer API, official MCP client, webhook browser | Two passed |
| Authentication browser/OAuth handoff fixture | Three passed; not a real Google login |
| Gmail lifecycle and safety browser fixture | Two passed; no real customer messages sent |
| Production backup/restore/schema upgrade rehearsal | Running in private local PostgreSQL 18; production source read-only |
| Release image build | Build `03a25369-aeae-463c-8b48-9d30328442f5` succeeded; no service promotion yet |

## Genuine owner actions

1. Complete the previously approved Vercel team upgrade to a commercial-eligible
   plan. A successful CLI login does not change the plan.
2. Approve exact additional publisher endpoints and usage/retention terms before
   Stack Exchange, RSS/Atom or Discourse activation. Public availability and a key
   alone are not approval. Hacker News acceptance is tracked separately.
3. Complete the real Google sign-in/consent handoff if the browser requires owner
   interaction. No replacement credentials or service-account keys are requested.

Independent AI evaluation, reviewed acceptance thresholds and pricing inputs remain
separate quality/cost limitations; local functional success is not a quality or
commercial-readiness certification.

## GitHub and deployment record

- Current source baseline: `601f6c4aedfb37d44add8bf42b2addd48fa1b8f2`.
- Remote main last verified: `03398f62a3c040e2220157fd7726d7c1233c6969`.
- Current release changes are not yet committed/pushed. Outgoing baseline scan
  found no oversized, generated/private or current-credential-bearing blobs.
- Vercel live URL remains the old deployment above; no new Vercel deployment is
  represented as live.
- Release images: existing Artifact Registry `querryside/leadengine`, tags
  `api:beta-20261113-r1` and `worker:beta-20261113-r1`; Python 3.12, current lockfile.
- Dashboard runtime: Node 24; existing Google OAuth/session and signed API gateway.

Live outreach, new acquisition runs, public signup, retired SEO/security audit
modules and unapproved sources are outside this activation. Existing contact and
suppression history must survive the recovery-tested additive upgrade.
