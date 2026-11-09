"""Recorded qualification/resource evidence, without inventing historical metrics."""
import json
from collections import Counter

def campaign_diagnostics(c,cid):
    rows=c.execute('SELECT b.id,b.rejection_reason,b.processing_status,b.website_status,b.source_tags_json FROM businesses b JOIN pipeline_runs r ON r.id=b.run_id WHERE r.campaign_id=?',(cid,)).fetchall()
    reasons=Counter();gate_counts=Counter();new_flow=False
    for row in rows:
        gate=json.loads(row['source_tags_json'] or '{}').get('qualification',{})
        new_flow|=bool(gate)
        if row['processing_status']!='QUALIFIED':reasons[row['rejection_reason'] or 'NOT_PROCESSED']+=1
    events=c.execute("SELECT e.run_id,e.metadata_json FROM pipeline_run_events e JOIN pipeline_runs r ON r.id=e.run_id WHERE r.campaign_id=? AND e.event_type='EMAIL_GATE_COMPLETE' ORDER BY e.id",(cid,)).fetchall()
    latest={r['run_id']:json.loads(r['metadata_json'] or '{}') for r in events}
    for value in latest.values():gate_counts.update({k:v for k,v in value.items() if isinstance(v,int)})
    operations=c.execute('SELECT a.analyzer,a.operation,COUNT(*) n FROM analysis_operations a JOIN pipeline_runs r ON r.id=a.run_id WHERE r.campaign_id=? GROUP BY a.analyzer,a.operation',(cid,)).fetchall()
    by_analyzer=Counter();reused=0
    for row in operations:
        if row['operation']=='REUSED':reused+=row['n']
        else:by_analyzer[row['analyzer']]+=row['n']
    return {'new_qualification_flow':new_flow,'rejections':dict(reasons),'email':dict(gate_counts),'resources':{'websites_probed':sum(r['website_status'] in ('REACHABLE','UNREACHABLE') for r in rows),'emails_searched':gate_counts['email_searched'],'deep_crawls':by_analyzer['crawl'],'technical_audits':by_analyzer['website'],'seo_audits':by_analyzer['seo'],'security_audits':by_analyzer['security'],'lighthouse_runs':by_analyzer['lighthouse'],'analysis_reused':reused,'deep_audits_skipped':gate_counts['deep_audits_skipped']}}

def source_funnel(result):
    """Prospecting metrics; historical assessment metrics have a separate field."""
    old=result['funnel'];counts=(result.get('acquisition') or {}).get('counts',{});source=result.get('source_type','OVERTURE')
    shared={key:old.get(key,0) for key in ('qualified','email_eligible','manual_contact','needs_review','emails_sent','replies','meetings','won')}
    if source=='FIRECRAWL':
        return {'search_results':counts.get('search_results',0),'businesses_found':counts.get('businesses_found',0),'websites_found':counts.get('websites_found',counts.get('normalized',0)),'emails_found':counts.get('emails_found',counts.get('qualified',0)),'contactable_leads':counts.get('unique_businesses',0),'company_information':counts.get('analyzed',0),'campaign_leads':result['qualified'],**shared}
    if source in ('FILE_IMPORT','GOOGLE_SHEETS'):
        return {'rows':counts.get('rows_read',0),'mapped':counts.get('rows_read',0),'valid_rows':counts.get('valid_rows',0),'duplicates':counts.get('duplicates',0),'qualified_imported':result['qualified'],'company_information':counts.get('analyzed',0),'information_failed':counts.get('analysis_failed',0),'information_unavailable':counts.get('analysis_not_available',0),**shared}
    return {key:old.get(key,0) for key in ('raw_discovered','observations','unique_businesses','rejected')}|{'company_information':sum(r.get('websites_processed',0) or 0 for r in result['scans']),**shared}
