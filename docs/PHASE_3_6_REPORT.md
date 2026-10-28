# Phase 3.6 delivery report

## Delivered

- Existing architecture, Google allowlist, signed API boundary, private storage, report versioning and opportunity scoring are preserved.
- Eight-platform canonical social discovery reuses the shared crawl and retained OSM/Overture metadata. Public activity is bounded and evidence-based; restrictions and missing dates remain UNKNOWN.
- Versioned scale V2 adds MID_MARKET (6–25 observed locations), default Local/Small Group/Mid Market targeting, optional multi-size filters and commercial-fit sorting. A 15-location independent dental fixture remains MID_MARKET.
- Scan-time anonymous public homepage capture stores private images. PDF workers consume stored images without fetching websites.
- PlaneByte client reports retain the supplied orange branding, measured current scores and proposed target gains. They add strongest priorities, evidence/impact/recommendations, a delivery roadmap and configurable included-services offer. Multi-location reports include a tailored rollout/governance section. No invented prices or financial outcomes are used.
- Campaign, scan and lead deletion previews require DELETE, block active workers/reports, remove private artifacts and all report versions, preserve shared canonical leads outside a deleted campaign/scan and support retry after partial storage cleanup.

## Deployment

- Dashboard: https://leads.planebyte.com
- API revision: leadengine-api-00010-tvl
- API image: asia-south1-docker.pkg.dev/querryside/leadengine/api:phase36-validated-20261026-200408
- Worker image: asia-south1-docker.pkg.dev/querryside/leadengine/worker:phase36-validated-20261026-200408
- Schema: 6, additive migration only. No production history import/reclassification was performed.
- Resource limits and existing IAM/secrets were preserved.

## Validation

- Final full Linux backend regression: 182 passed, 3 opt-in PostgreSQL checks skipped there.
- All 3 real PostgreSQL checks passed separately in disposable schemas, including permanent deletion.
- Latest focused feature suite: 47 passed, including missing optional source metadata and worker queue handoff regressions.
- Dashboard: 45 unit checks, strict TypeScript, lint, production build and 4 browser checks passed.
- Production deletion QA: {"businesses_removed": true, "pipeline_runs_removed": true, "private_objects_removed": true, "prospects_removed": true, "scan_campaigns_removed": true}. Only newly created labeled QA records were deleted.
- Previous client report bytes preserved: True.
- Automated app checks use a short-lived allowlisted session, not a newly completed Google login. Fresh Google authentication and private R2 account settings were previously confirmed by the user.

## Live campaign and measurements

- Campaign: a15e9d59-91b4-48ec-8a08-6985fb5c3e29; London, United Kingdom / Dentists; target 10; Small Group + Mid Market; all analyzers and social checks enabled.
- Status: COMPLETED; counters: {"raw_found": 192, "qualified": 0, "exported": 0}.
- Assessed: 40; profiles: 60; activity verified: 0; UNKNOWN: 60.
- Social requests: 52; maximum per business: 4; requests/assessed business: 1.3.
- Aggregate per-business social wall time: 143.71 seconds. Businesses run at concurrency 2; this sum is not campaign elapsed time and is not a pre/post causal benchmark.
- Measured social-stage elapsed time, including metadata persistence: 133.891 seconds, from the recorded audit-complete and social-complete events.
- Scale distribution: {"REGIONAL": 1, "LOCAL": 39}; qualified scale distribution: {}.
- The original v2.0.0 campaign's one REGIONAL entry used a missing-value hostname and is invalidated as scale evidence. Version 2.0.1 fixes that input handling and records corrected classifications in the follow-up observations. No real mid-market match was found in this sample.
- Private captures ready: 2; unavailable: 2. An unavailable image is explicitly labeled and never fabricated.
- STALE profiles missing dated supporting evidence: 0.

### Bounded follow-up re-audit

The group-only campaign found no qualifying size matches among the sampled businesses. A separate four-observation re-audit reuses genuine records from that discovery, includes Local businesses and caps Lighthouse at one check. It does not invent a mid-market result. The missing-website observation is corrected only in a new versioned observation; historical records remain intact.

{"id": 46, "status": "COMPLETED", "raw_found": 4, "qualified": 4, "exported": 4, "started_at": "2026-10-26 14:39:56.759336+00", "finished_at": "2026-10-26 14:45:19.849328"}

New classification versions: {"scale-2.0.1": 4}.

## Report variants

{
  "reachable": {
    "pages": 9,
    "bytes": 2478941,
    "mid_market_fixture": false,
    "stored_screenshot_embedded": true,
    "all_pages_rasterized_and_visually_reviewed": true
  },
  "mid-market": {
    "pages": 11,
    "bytes": 1308043,
    "mid_market_fixture": true,
    "stored_screenshot_embedded": false,
    "all_pages_rasterized_and_visually_reviewed": true
  },
  "no-website": {
    "pages": 5,
    "bytes": 1282781,
    "mid_market_fixture": false,
    "stored_screenshot_embedded": false,
    "all_pages_rasterized_and_visually_reviewed": true
  },
  "unreachable": {
    "pages": 5,
    "bytes": 1283022,
    "mid_market_fixture": false,
    "stored_screenshot_embedded": false,
    "all_pages_rasterized_and_visually_reviewed": true
  }
}

Every final variant is rasterized for visual inspection. The mid-market layout sample is explicitly labeled QA when no real mid-market observation is available; it is not a client deliverable for an invented business.

## Live issues found and resolved

1. Optional Overture social JSON columns can arrive as missing dataframe values. A tolerant typed decoder now retains the business and taxonomy instead of dropping the provider result. Seven missing-data fixtures cover the regression.
2. Report-worker queue handoff imported the scan-manager singleton through the executor base class and could fail after successfully writing the PDF. The executor contract now lives in a dependency-free module. A fresh-process import regression and live job verification cover the fix.
3. Missing website text could previously be serialized as a literal NaN hostname and distort shared-domain footprint counts. Scale version 2.0.1 rejects invalid professional domains; new source observations retain missing fields as null. Historical observations are preserved.
4. The first London attempt returned zero after the source parser failure and fallback service errors. It is retained as an acceptance attempt, not represented as successful business evidence.

## Evidence and operation notes

See phase36-production.json, phase36-status.json, phase36-measurements.json, phase36-deletion-qa.json, phase36-worker-canary.json, phase36-r2-privacy.json and phase36-pdf-qa.json. Supporting guides: SOCIAL_ENRICHMENT.md, BUSINESS_SCALE_V2.md, CLIENT_REPORT_V2.md and PERMANENT_DELETION.md.

External source availability and social access restrictions can vary. UNKNOWN activity remains neutral; footprint counts are observed lower bounds, and commercial fit does not estimate revenue, employees or budget.
