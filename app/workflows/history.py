"""Immutable campaign evidence, separate from replaceable analysis cache entries."""
import hashlib,json
from datetime import datetime,timezone
from app.database.foundation_schema import ready
from app.database.prospects import now

def encoded(value):return json.dumps(value,sort_keys=True,separators=(',',':'),default=str)

def signature(settings):
    keys=('countries','cities','locations','verticals','business_scales','commercial_fit','opportunities','crawler','auditing','social','quality','exclude_chains','icp_id','product_flow')
    keys=(*keys,*(key for key in ('scan_source','source_type','processing_policy','qualification_mode','preliminary_opportunity_threshold','qualified_score_threshold') if key in settings))
    def normalize(v,key=None):
        if isinstance(v,dict):return {k:normalize(v[k],k) for k in sorted(v)}
        if isinstance(v,(list,tuple)):
            values=[normalize(x) for x in v]
            return values if key=='bbox' else sorted(values,key=encoded)
        return v.strip().casefold() if isinstance(v,str) else v
    return hashlib.sha256(encoded(normalize({k:settings.get(k) for k in keys})).encode()).hexdigest()

def campaign_org(c,cid):
    row=c.execute('SELECT organization_id FROM scan_campaigns WHERE id=?',(cid,)).fetchone()
    return row['organization_id'] if row else None

def effective(c,options,organization=None):
    from app.config.workspace import load_settings
    from app.api.organization import workspace_settings
    from app.config.settings import get_settings
    shared=load_settings(c,organization).model_dump()
    environment=get_settings()
    result=dict(options)
    for section in ('crawler','auditing'):
        result.setdefault(section,shared[section])
    if options.get('product_flow')=='PROSPECTING_V1':
        from app.prospecting.policy import configuration
        result=configuration(result)
        result['crawler']={**result['crawler'],'max_pages':min(3,result['crawler'].get('max_pages',3))}
        result['auditing']={key:False if isinstance(value,bool) else value for key,value in result['auditing'].items()}
    result.setdefault('analysis_mode','INCREMENTAL')
    result.setdefault('social',{'enabled':environment.social_enrichment_enabled,'activity_enabled':environment.social_activity_enabled})
    stored=workspace_settings(c,organization)
    foundation=(stored or {}).get('foundation',{})
    from app.pipeline.reuse import WINDOWS
    result.setdefault('reuse_windows',foundation.get('reuse_windows',WINDOWS))
    return result

def capture_settings(c,cid,options,schedule_id=None,provenance='EFFECTIVE_AT_START',organization=None):
    if not ready(c):return options
    organization=organization or campaign_org(c,cid)
    prior=c.execute('SELECT settings_json FROM campaign_settings_snapshots WHERE campaign_id=?',(cid,)).fetchone()
    if prior:return json.loads(prior[0])
    value=effective(c,options,organization=organization) if provenance=='EFFECTIVE_AT_START' else dict(options)
    c.execute('INSERT INTO campaign_settings_snapshots(campaign_id,signature,settings_json,captured_at,provenance,source_schedule_id,organization_id) VALUES(?,?,?,?,?,?,?) ON CONFLICT(campaign_id) DO NOTHING',
              (cid,signature(value),encoded(value),now(),provenance,schedule_id,organization))
    return value

def settings(c,cid):
    row=c.execute('SELECT * FROM campaign_settings_snapshots WHERE campaign_id=?',(cid,)).fetchone()
    return {**dict(row),'settings':json.loads(row['settings_json'])} if row else None

def previous(c,cid):
    current=settings(c,cid)
    if not current:return []
    return [dict(r) for r in c.execute('SELECT h.campaign_id,h.captured_at,s.target_total,s.status FROM campaign_settings_snapshots h JOIN scan_campaigns s ON s.id=h.campaign_id WHERE h.signature=? AND h.campaign_id<>? AND h.captured_at<? ORDER BY h.captured_at DESC LIMIT 30',(current['signature'],cid,current['captured_at'])).fetchall()]

def capture_business(c,cid,business_id):
    if not ready(c) or not cid:return
    b=c.execute('SELECT * FROM businesses WHERE id=?',(business_id,)).fetchone()
    if not b or not b['prospect_id']:return
    def rows(table):return [dict(r) for r in c.execute('SELECT * FROM '+table+' WHERE business_id=?',(business_id,)).fetchall()]
    payload={'business':dict(b),'findings':rows('findings'),'opportunity':rows('opportunity_scores'),'intelligence':rows('business_intelligence'),'profile':rows('website_profiles'),'lighthouse':rows('lighthouse_results')}
    c.execute('INSERT INTO campaign_business_snapshots(campaign_id,business_id,prospect_id,snapshot_json,captured_at,organization_id) VALUES(?,?,?,?,?,?) ON CONFLICT(campaign_id,business_id) DO NOTHING',(cid,business_id,b['prospect_id'],encoded(payload),now(),campaign_org(c,cid)))

def snapshots(c,cid):
    return {r['prospect_id']:json.loads(r['snapshot_json']) for r in c.execute('SELECT prospect_id,snapshot_json FROM campaign_business_snapshots WHERE campaign_id=? ORDER BY business_id',(cid,)).fetchall()}

def capture_run(c,cid,run_id):
    if not cid or not ready(c):return
    from collections import defaultdict
    records={}
    for label,table in [('findings','findings'),('opportunity','opportunity_scores'),('intelligence','business_intelligence'),('profile','website_profiles'),('lighthouse','lighthouse_results')]:
        groups=defaultdict(list)
        for r in c.execute('SELECT * FROM '+table+' WHERE business_id IN (SELECT id FROM businesses WHERE run_id=?)',(run_id,)).fetchall():groups[r['business_id']].append(dict(r))
        records[label]=groups
    rows=[];stamp=now();organization=campaign_org(c,cid)
    for b in c.execute('SELECT * FROM businesses WHERE run_id=? AND prospect_id IS NOT NULL',(run_id,)).fetchall():
        payload={'business':dict(b),**{label:groups[b['id']] for label,groups in records.items()}}
        rows.append((cid,b['id'],b['prospect_id'],encoded(payload),stamp,organization))
    c.executemany('INSERT INTO campaign_business_snapshots(campaign_id,business_id,prospect_id,snapshot_json,captured_at,organization_id) VALUES(?,?,?,?,?,?) ON CONFLICT(campaign_id,business_id) DO NOTHING',rows)

def findings(value):
    return {f['finding_code'] for f in value.get('findings',[])}

def compare(c,cid,other):
    matches=previous(c,cid)
    if not other:other=matches[0]['campaign_id'] if matches else None
    if not other:return {'previous':None,'matches':matches,'businesses':[],'deltas':{}}
    if other not in {m['campaign_id'] for m in matches}:
        from fastapi import HTTPException
        raise HTTPException(422,'Choose an older campaign with matching effective settings.')
    current=snapshots(c,cid);before=snapshots(c,other);changes=[]
    for pid in sorted(set(current)|set(before)):
        a=current.get(pid);b=before.get(pid);new=findings(a or {})-findings(b or {});resolved=findings(b or {})-findings(a or {})
        state='NEW' if b is None else 'NO_LONGER_DISCOVERED' if a is None else 'CHANGED' if encoded(a)!=encoded(b) else 'UNCHANGED'
        # Observation IDs/timestamps are not business changes.
        if a and b:
            stable=lambda x:{'findings':sorted(findings(x)),'opportunity':[{k:v for k,v in o.items() if k.endswith('_score') or k=='primary_opportunity'} for o in x.get('opportunity',[])]}
            state='CHANGED' if encoded(stable(a))!=encoded(stable(b)) else 'UNCHANGED'
        changes.append({'prospect_id':pid,'company':(a or b)['business']['name'],'state':state,'new_findings':sorted(new) if a and b else [],'resolved_findings':sorted(resolved) if a and b else [],'unchanged_findings':sorted(findings(a)&findings(b)) if a and b else []})
    def metrics(cid,items):
        result={k:0 for k in ('raw_discovered','unique_businesses','qualified','email_eligible','manual_contact','average_opportunity','replies')}
        result['raw_discovered']=c.execute('SELECT COALESCE(SUM(raw_found),0) FROM pipeline_runs WHERE campaign_id=?',(cid,)).fetchone()[0]
        result['unique_businesses']=len(items);qualified=[v for v in items.values() if v['business']['processing_status']=='QUALIFIED'];result['qualified']=len(qualified)
        # Historical eligibility must not be inferred from today's suppression state.
        result['email_eligible']=None;result['manual_contact']=None;result['replies']=None
        scores=[max(o.get('website_opportunity_score') or 0,o.get('seo_opportunity_score') or 0,o.get('security_opportunity_score') or 0) for v in qualified for o in v['opportunity']]
        result['average_opportunity']=round(sum(scores)/len(scores),1) if scores else None
        return result
    a=metrics(cid,current);b=metrics(other,before)
    return {'previous':other,'matches':matches,'businesses':changes,'current':a,'before':b,'deltas':{k:a[k]-b[k] if a[k] is not None and b[k] is not None else None for k in a},'snapshot_counts':{'current':len(current),'previous':len(before)},'incomplete':not current or not before}
