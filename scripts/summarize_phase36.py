import json
from datetime import datetime
from collections import Counter
from pathlib import Path

def read(name,default=None):
    p=Path('docs')/name
    return json.loads(p.read_text(encoding='utf-8')) if p.exists() else default

state=read('phase36-production.json',{})
evidence=read('phase36-status.json',{})
rows=evidence.get('campaign_intelligence',[]);profiles=evidence.get('profiles',[]);captures=evidence.get('captures',[])+evidence.get('targeted_reaudit',{}).get('captures',[])
metrics=[json.loads(r['enrichment_metrics_json']) for r in rows]
requests=sum(m.get('requests',0) for m in metrics);seconds=sum(m.get('seconds',0) for m in metrics)
verified=sum(p['activity_status']!='UNKNOWN' for p in profiles);unknown=len(profiles)-verified
events={e['event_type']:datetime.fromisoformat(e['timestamp']) for e in evidence.get('campaign_events',[])}
social_wall=round((events['SOCIAL_COMPLETE']-events['AUDIT_COMPLETE']).total_seconds(),3) if all(k in events for k in ('SOCIAL_COMPLETE','AUDIT_COMPLETE')) else None
summary={'assessed_businesses':len(rows),'social_profiles':len(profiles),'verified_activity':verified,'unknown_activity':unknown,'unknown_rate':round(unknown/len(profiles),4) if profiles else None,'social_requests':requests,'requests_per_assessed_business':round(requests/len(rows),3) if rows else None,'aggregate_business_social_seconds':round(seconds,3),'maximum_requests_per_business':max((m.get('requests',0) for m in metrics),default=0),'business_scales':dict(Counter(r['business_scale'] for r in rows)),'qualified_scales':dict(Counter(r['business_scale'] for r in rows if r['processing_status']=='QUALIFIED')),'captures_ready':sum(c['status']=='READY' for c in captures),'captures_unavailable':sum(c['status']!='READY' for c in captures),'false_stale_without_evidence':sum(p['activity_status']=='STALE' and not(p.get('last_activity_at') and p.get('activity_evidence_url')) for p in profiles)}
Path('docs/phase36-measurements.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
summary['social_stage_wall_seconds']=social_wall
Path('docs/phase36-measurements.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
campaign=state.get('campaign',{});delete=read('phase36-deletion-qa.json',{});qa=read('phase36-pdf-qa.json',{});images=json.loads(Path('deploy/images.json').read_text(encoding='utf-8-sig'))
text=f'''# Phase 3.6 delivery report

## Delivered

- Existing architecture, Google allowlist, signed API boundary, private storage, report versioning and opportunity scoring are preserved.
- Eight-platform canonical social discovery reuses the shared crawl and retained OSM/Overture metadata. Public activity is bounded and evidence-based; restrictions and missing dates remain UNKNOWN.
- Versioned scale V2 adds MID_MARKET (6–25 observed locations), default Local/Small Group/Mid Market targeting, optional multi-size filters and commercial-fit sorting. A 15-location independent dental fixture remains MID_MARKET.
- Scan-time anonymous public homepage capture stores private images. PDF workers consume stored images without fetching websites.
- PlaneByte client reports retain the supplied orange branding, measured current scores and proposed target gains. They add strongest priorities, evidence/impact/recommendations, a delivery roadmap and configurable included-services offer. Multi-location reports include a tailored rollout/governance section. No invented prices or financial outcomes are used.
- Campaign, scan and lead deletion previews require DELETE, block active workers/reports, remove private artifacts and all report versions, preserve shared canonical leads outside a deleted campaign/scan and support retry after partial storage cleanup.

## Deployment

- Dashboard: https://leads.planebyte.com
- API revision: {images.get('revision')}
- API image: {images.get('api')}
- Worker image: {images.get('worker')}
- Schema: 6, additive migration only. No production history import/reclassification was performed.
- Resource limits and existing IAM/secrets were preserved.

## Validation

- Final full Linux backend regression: 182 passed, 3 opt-in PostgreSQL checks skipped there.
- All 3 real PostgreSQL checks passed separately in disposable schemas, including permanent deletion.
- Latest focused feature suite: 47 passed, including missing optional source metadata and worker queue handoff regressions.
- Dashboard: 45 unit checks, strict TypeScript, lint, production build and 4 browser checks passed.
- Production deletion QA: {json.dumps(delete,sort_keys=True)}. Only newly created labeled QA records were deleted.
- Previous client report bytes preserved: {state.get('checks',{}).get('previous_reports_unchanged','pending')}.
- Automated app checks use a short-lived allowlisted session, not a newly completed Google login. Fresh Google authentication and private R2 account settings were previously confirmed by the user.

## Live campaign and measurements

- Campaign: {campaign.get('id','pending')}; London, United Kingdom / Dentists; target 10; Small Group + Mid Market; all analyzers and social checks enabled.
- Status: {campaign.get('status','pending')}; counters: {json.dumps(campaign.get('counters',{}))}.
- Assessed: {summary['assessed_businesses']}; profiles: {summary['social_profiles']}; activity verified: {verified}; UNKNOWN: {unknown}.
- Social requests: {requests}; maximum per business: {summary['maximum_requests_per_business']}; requests/assessed business: {summary['requests_per_assessed_business']}.
- Aggregate per-business social wall time: {summary['aggregate_business_social_seconds']} seconds. Businesses run at concurrency 2; this sum is not campaign elapsed time and is not a pre/post causal benchmark.
- Measured social-stage elapsed time, including metadata persistence: {social_wall} seconds, from the recorded audit-complete and social-complete events.
- Scale distribution: {json.dumps(summary['business_scales'])}; qualified scale distribution: {json.dumps(summary['qualified_scales'])}.
- The original v2.0.0 campaign's one REGIONAL entry used a missing-value hostname and is invalidated as scale evidence. Version 2.0.1 fixes that input handling and records corrected classifications in the follow-up observations. No real mid-market match was found in this sample.
- Private captures ready: {summary['captures_ready']}; unavailable: {summary['captures_unavailable']}. An unavailable image is explicitly labeled and never fabricated.
- STALE profiles missing dated supporting evidence: {summary['false_stale_without_evidence']}.

### Bounded follow-up re-audit

The group-only campaign found no qualifying size matches among the sampled businesses. A separate four-observation re-audit reuses genuine records from that discovery, includes Local businesses and caps Lighthouse at one check. It does not invent a mid-market result. The missing-website observation is corrected only in a new versioned observation; historical records remain intact.

{json.dumps(evidence.get('targeted_reaudit',{}).get('run',{}))}

New classification versions: {json.dumps(dict(Counter(r['classification_version'] for r in evidence.get('targeted_reaudit',{}).get('intelligence',[]))))}.

## Report variants

{json.dumps(qa,indent=2)}

Every final variant is rasterized for visual inspection. The mid-market layout sample is explicitly labeled QA when no real mid-market observation is available; it is not a client deliverable for an invented business.

## Live issues found and resolved

1. Optional Overture social JSON columns can arrive as missing dataframe values. A tolerant typed decoder now retains the business and taxonomy instead of dropping the provider result. Seven missing-data fixtures cover the regression.
2. Report-worker queue handoff imported the scan-manager singleton through the executor base class and could fail after successfully writing the PDF. The executor contract now lives in a dependency-free module. A fresh-process import regression and live job verification cover the fix.
3. Missing website text could previously be serialized as a literal NaN hostname and distort shared-domain footprint counts. Scale version 2.0.1 rejects invalid professional domains; new source observations retain missing fields as null. Historical observations are preserved.
4. The first London attempt returned zero after the source parser failure and fallback service errors. It is retained as an acceptance attempt, not represented as successful business evidence.

## Evidence and operation notes

See phase36-production.json, phase36-status.json, phase36-measurements.json, phase36-deletion-qa.json, phase36-worker-canary.json, phase36-r2-privacy.json and phase36-pdf-qa.json. Supporting guides: SOCIAL_ENRICHMENT.md, BUSINESS_SCALE_V2.md, CLIENT_REPORT_V2.md and PERMANENT_DELETION.md.

External source availability and social access restrictions can vary. UNKNOWN activity remains neutral; footprint counts are observed lower bounds, and commercial fit does not estimate revenue, employees or budget.
'''
Path('docs/PHASE_3_6_REPORT.md').write_text(text,encoding='utf-8');print(json.dumps(summary))
