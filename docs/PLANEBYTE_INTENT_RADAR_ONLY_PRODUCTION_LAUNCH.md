# Intent Radar-only production release

Status: **LIMITED GO — existing authorized owner Beta deployed. Public commercial launch: NO-GO.** This is not public-launch approval.

## Preservation baseline

Starting commit: `49e7f9e383fc8bceb58eed63b15c9f4e3873afc3`.
The private baseline records 1,536 tracked source files, 174 PostgreSQL tables,
schema version 46, counts for 51 Lead Engine-related tables and all stored
Lead Engine entitlement rows. No production migration, reset or cleanup is part
of this release. Existing recovery evidence includes a verified backup restored
on PostgreSQL 18.7, with original columns/history preserved across schema 45→46.

All Lead Engine route files, services, workers, tests, configuration, shared
libraries, data, suppression/contact history and integration credentials remain
in this repository/database. The product selector implementation is retained but
is not mounted in the Intent-only production shell. The marketing directory and
Netlify site are outside this release.

## Reversible availability

One server-only configuration controls availability: `LEAD_ENGINE_AVAILABLE`.
Its default is `false`. Production API, workers and the existing Vercel project
use `false`. It is separate from `LEAD_ENGINE_PUBLIC_ENABLED`, which controls
new enrollment and remains false.

The effective product response excludes LEADGEN when unavailable. Stored manual
and billing entitlements are not deleted or rewritten. Legacy pages remain on
disk, but authenticated direct frontend requests redirect to `/intent-radar`.
Lead Engine APIs and scoped credentials cannot bypass product availability;
workflow dispatch stops without advancing schedules or changing run state.
Shared company setup, ICPs, authentication, billing, Radar/Growth jobs, account
security, MCP and existing inbox synchronization are preserved.

To re-enable Lead Engine in a future **approved release**:

1. Set `LEAD_ENGINE_AVAILABLE=true` on the existing FastAPI service and existing
   worker/acquisition/canary jobs in project `querryside`, region `asia-south1`.
   Preserve each resource's other environment and Secret Manager references.
2. Set the same server-only value to `true` in the existing Vercel production
   project, build and promote that verified release through its Git integration.
3. Run the preserved Lead Engine, Gmail and cross-workspace regression suite.
   Existing grants determine which workspace can access the restored product.
4. Keep public enrollment and delivery/acquisition flags unchanged unless
   separately approved. Making the product available does not authorize sends,
   scans, public registration or new customer grants.

No feature reconstruction, data recovery, migration or restoration of deleted
records is required. Isolated tests verify config-only reactivation restores the
same company record and pre-existing API credential.

## Production issue found during acceptance

The deployed overview returned HTTP 500 on PostgreSQL: the trend query used
`day` as an unquoted SQL alias. The query now quotes this identifier, preserving
its response contract. A real isolated PostgreSQL regression covers empty and
populated trends plus cross-workspace separation. Failed server access checks
have a bounded, explicit retry state, separate from genuinely restricted access.

## Test Mode billing status

Razorpay remains Test Mode, restricted to the approved owner workspace. Public
paid checkout and live charges remain disabled. The controlled subscription is
cancelled. Two independently verified captured sandbox payments remain in
history. A real failed recurring charge and pending-state reconciliation were
verified; extra accelerated sandbox charges hit the provider's per-cycle mandate
limit and were stopped. No production price or payment authorization is implied.

The live HMAC webhook URL remains:
`https://leadengine-api-befca7xg4a-el.a.run.app/api/billing/webhooks/razorpay`.
The enabled Dashboard entry has ten subscription lifecycle events. The redundant
entry was reversibly disabled. Genuine pending events were received and processed.

## Release gates and evidence

Private evidence: `data/artifacts/verification/intent-only/`.
Exact source/deployment identifiers and final results are recorded below. Interrupted diagnostic runs and actual failures are retained.
A full suite, production build, responsive acceptance and live owner browser
acceptance must pass before promotion is described as verified.

## Public launch boundary

The authorized owner Beta is separate from an unrestricted public commercial
launch. Independent 120-case AI evaluation still needs two independent reviewers
and an adjudicator; no human labels or pass result has been fabricated. Approved
commercial plans, live payment authorization and canonical public legal terms
are not supplied. Public registration/checkout stay closed. These are genuine
public-launch gates, not reasons to stop this restricted production release.

### Verified local release gates

- Backend, security, tenant isolation, preserved Lead Engine/Gmail behavior and
  isolated PostgreSQL: **971 passed, 1 intentional live-email skip**, 7 existing
  deprecation/report-format warnings. No failed tests.
- Frontend: **156 unit tests passed**; production build and type checking passed.
- Integrated signed-gateway browser checks: **8 passed** (Growth research 2,
  restricted Test Mode billing 2, Intent-only desktop/tablet/mobile and denied
  workspace 4). Public sources/AI in these local checks use explicit synthetic
  fixtures; they are not represented as real provider acceptance.
- Production acceptance identified the PostgreSQL overview failure before
  promotion. The dedicated PostgreSQL overview regression also passed.
- Outgoing source scan: no credential matches, private artifacts or generated
  build directories staged; no tracked file deletions. The separate untracked
  marketing work is excluded.

### Future approved reactivation commands

Run these only as part of an owner-approved release; do not execute them for
this Intent-only launch:

```sh
gcloud run services update leadengine-api --project=querryside --region=asia-south1 --update-env-vars=LEAD_ENGINE_AVAILABLE=true
gcloud run jobs update leadengine-worker --project=querryside --region=asia-south1 --update-env-vars=LEAD_ENGINE_AVAILABLE=true
gcloud run jobs update leadengine-acquisition --project=querryside --region=asia-south1 --update-env-vars=LEAD_ENGINE_AVAILABLE=true
gcloud run jobs update leadengine-quota-canary --project=querryside --region=asia-south1 --update-env-vars=LEAD_ENGINE_AVAILABLE=true
printf true | vercel env update LEAD_ENGINE_AVAILABLE --environment=production --sensitive --yes --scope=piyushagrawal6s-projects
```

Then redeploy the verified existing Vercel project with that configuration,
verify the exact Git commit and promote its READY deployment to the existing
production domain. No new frontend provider or database operation is required.
Existing product grants and global delivery safeguards still apply.


## Deployed release and final verification

- Production: **https://app.planebyte.com**; existing Vercel project `leadengine`.
- Application release commit: `ca4e374742a5e49f25e05e2a1a51d8a9bc700cd3`, pushed
  normally to GitHub main; no force push.
- Vercel deployment: `dpl_7ZxaDYsLyXzBdjwDXA8mAjTym9Da`, READY and explicitly
  promoted. The production domain's alias was independently verified against
  that exact deployment. The preview URL retains Vercel deployment protection.
- FastAPI: `leadengine-api-00132-kas`, 100% production traffic in the existing
  Cloud Run service. API/worker image tags: `intent-only-ca4e374742`.
- Existing `leadengine-worker`, `leadengine-acquisition`, and
  `leadengine-quota-canary` use the verified worker image. Commands, identities,
  other environment variables and Secret Manager references were compared with
  their pre-release snapshots and remain unchanged.
- All nine older tagged API URLs now route to the same verified revision, closing
  stale-version entry points. Historical revisions were retained; their previous
  routing is recorded in the private rollback evidence. No service was deleted.
- PostgreSQL remains **schema 46**, all **174 original tables** are present, and
  counts for all 51 checked Lead Engine-related tables did not decrease. Stored
  Lead Engine grants are exactly unchanged. There were **zero tracked file
  deletions**. A focused blob comparison confirms **132 core Lead Engine, Gmail,
  discovery, integration, worker and database implementation files unchanged**.
- No production migration, cleanup, outbound email, prospect discovery or real
  payment was initiated by this release. Existing no-send/no-acquisition flags,
  closed registration and restricted billing controls remain intact. Scheduler
  configuration/state was compared and preserved. Existing inbox sync continues.

### Actual production checks

Ten authentication/security checks passed: unsigned/invalid/unapproved/replayed
requests denied, approved signed owner request allowed, untrusted CORS not
granted, API schema hidden, oversized input rejected, Razorpay HMAC required,
and neighboring webhook routes remain authenticated.

Thirteen staged read smoke checks passed, including shared company/ICP setup,
Radar capabilities/overview, Growth overview and Test Mode billing. Lead Engine
workflow, mailbox, provider configuration, settings and assistant APIs return
404 under this release policy. The live login returns 200 with Intent Radar
branding and security headers; anonymous root requests redirect to login.

Native Chrome acceptance used the existing real `planebyte@gmail.com` Google
session: the new static Intent Radar identity and absent product selector were
visible, the overview rendered actual stored signals (5 new, 1 reviewed, 1 active
monitor), and the Growth research reports screen rendered. No new search, AI
job, message or checkout was started in these final browser checks. The complete
signed local workflow regressions above use explicit fixtures; they are distinct
from these real production observations.

The actual controlled Razorpay cancellation event is **PROCESSED**. Captured
sandbox payment history remains intact. API reads report the controlled
subscription cancelled and two verified payments. No new mandate was created.

### Remaining gates and limitations

This is a functional restricted owner Beta, **not an unrestricted public launch**:

1. Production overview latency measured **48.32 seconds**. A read of
   `/api/intent-radar/sources/health` exceeded its **65-second** client timeout.
   Public performance/source-health acceptance therefore remains **NOT PASSED**.
   Diagnose and reduce the read/query work, then repeat deployed measurements.
   These observations do not establish that any particular upstream provider is
   offline. The client has bounded requests and explicit retry/error states.
2. The approved 120-case independent AI evaluation needs two independent human
   reviewers and an adjudicator. Its existing quality thresholds are unchanged;
   there is no fabricated human labeling or pass result.
3. Public commercial pricing, live payment authorization and canonical public
   legal/privacy terms still require owner approval. Razorpay Test Mode is not a
   public paid offering. Public registration and public checkout remain closed.
4. Vertex configuration/gateway and source adapters are preserved. Previous
   controlled runtime acceptance remains recorded; this release did not consume
   additional AI/discovery credits to repeat it. No fresh-provider-readiness
   claim is substituted for the timed-out source-health check.

Lead Engine can be restored through the approved configuration-only steps above,
without rebuilding any features or recovering deleted data. Full public launch
is deliberately not declared complete while these gates remain outstanding.
