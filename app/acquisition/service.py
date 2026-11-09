"""Source orchestration uses existing campaigns; never creates an outreach run."""
import json,uuid,hashlib
from datetime import datetime,timedelta,timezone
from tempfile import NamedTemporaryFile
from pathlib import Path
from fastapi import HTTPException
from app.database.prospects import now
from app.storage import artifact_storage
from app.acquisition.imports import Spreadsheet,filename,ImportInvalid
from app.acquisition.models import ProcessingOptions,ColumnMapping,Budgets
from app.acquisition.policy import policy

def encoded(v):return json.dumps(v,sort_keys=True,separators=(',',':'),default=str)
def event(c,jid,stage,message,counts=None):
    c.execute('INSERT INTO acquisition_events(id,job_id,stage,message,counts_json,created_at) VALUES(?,?,?,?,?,?)',(str(uuid.uuid4()),jid,stage,message[:400],encoded(counts or {}),now()))
def job(c,jid,actor=None):
    from app.platform.context import organization
    org=organization()
    r=c.execute('SELECT * FROM acquisition_jobs WHERE id=? AND organization_id=?',(jid,org)).fetchone()
    if not r:raise HTTPException(404,'Acquisition not found.')
    r=dict(r)
    if actor and r['owner']!=actor:raise HTTPException(403,'This staged source belongs to another account.')
    return r

def detail(c,jid,page=1,size=25):
    r=job(c,jid)
    result={k:r[k] for k in ('id','campaign_id','source_type','status','owner','cursor','error_code','error_message','created_at','updated_at','finished_at')}
    for key in ('configuration','origin','mapping','manifest','counts'):result[key]=json.loads(r[key+'_json']) if r[key+'_json'] else None
    result['events']=[{**dict(x),'counts':json.loads(x['counts_json'])} for x in c.execute('SELECT * FROM acquisition_events WHERE job_id=? ORDER BY created_at DESC,id DESC LIMIT 60',(jid,)).fetchall()]
    result['issues']={'items':[dict(x) for x in c.execute('SELECT row_number,reason,created_at FROM acquisition_issues WHERE job_id=? ORDER BY row_number LIMIT ? OFFSET ?',(jid,size,(page-1)*size)).fetchall()],'total':c.execute('SELECT COUNT(*) FROM acquisition_issues WHERE job_id=?',(jid,)).fetchone()[0],'page':page,'page_size':size}
    result['can_retry']=r['status'] in ('FAILED','DEGRADED') or r['status']=='RUNNING' and bool(r['lease_until'] and r['lease_until']<now())
    if r['campaign_id']:
        result['counts']['review_cases']=c.execute("SELECT COUNT(*) FROM review_cases WHERE campaign_id=? AND status='OPEN'",(r['campaign_id'],)).fetchone()[0]
        result['pipeline_events']=[dict(x) for x in c.execute('SELECT e.stage,e.message,e.timestamp FROM pipeline_run_events e JOIN pipeline_runs p ON p.id=e.run_id WHERE p.campaign_id=? ORDER BY e.id DESC LIMIT 20',(r['campaign_id'],)).fetchall()]
        result['scans']=[dict(x) for x in c.execute('SELECT id,market,vertical,status,raw_found,websites_processed,qualified,error_message FROM pipeline_runs WHERE campaign_id=? ORDER BY id',(r['campaign_id'],)).fetchall()]
        if r['status'] not in ('QUEUED','RUNNING'):
            from app.workflows.campaigns import campaign_summary
            summary=campaign_summary(c,r['campaign_id']);result['audience']={k:summary[k] for k in ('qualified','email_eligible','manual_contact','needs_review','suppressed','already_contacted','will_queue')}
    return result

def create_job(c,source,actor,key,configuration,origin,status='QUEUED'):
    from app.platform.context import organization
    org=organization()
    prior=c.execute('SELECT * FROM acquisition_jobs WHERE request_key=? AND organization_id=?',(key,org)).fetchone()
    if prior:
        if prior['owner']!=actor or prior['source_type']!=source or prior['configuration_json']!=encoded(configuration) or prior['origin_json']!=encoded(origin):raise HTTPException(409,'Request ID already belongs to different source content.')
        return dict(prior)
    jid=str(uuid.uuid4());stamp=now()
    c.execute('INSERT INTO acquisition_jobs(id,source_type,status,owner,request_key,configuration_json,origin_json,created_at,updated_at,organization_id) VALUES(?,?,?,?,?,?,?,?,?,?)',(jid,source,status,actor,key,encoded(configuration),encoded(origin),stamp,stamp,org))
    event(c,jid,'REVIEWED' if status=='QUEUED' else 'UPLOADED','Reviewed source queued for acquisition.' if status=='QUEUED' else 'Private source staged; no leads have been imported.')
    return job(c,jid)

def create_campaign(c,jid,name,prompt=None,target=None):
    r=job(c,jid)
    from app.platform.context import organization
    org=organization(r['organization_id'])
    if r['campaign_id']:return r['campaign_id']
    options=json.loads(r['configuration_json']);origin=json.loads(r['origin_json']);cid=str(uuid.uuid4())
    intent=options.get('intent',{});processing=options.get('processing',{})
    configuration={'name':name[:120],'kind':'SCAN','target':target or intent.get('targetQualifiedLeads',50),'countries':intent.get('countries') or [processing.get('default_country','United Kingdom')],'cities':intent.get('cities') or [processing.get('default_city') or 'Imported selection'],'verticals':intent.get('verticals') or [processing.get('default_vertical','hospitality')],'opportunities':[],'search_criteria':intent.get('search_criteria',{}),'business_scales':intent.get('businessSizes') or ['LOCAL','SMALL_GROUP','MID_MARKET'],'commercial_fit':['HIGH','MEDIUM'],'lighthouse_enabled':False,'source_type':r['source_type'],'processing_policy':policy(r['source_type']).mode.value,'acquisition_job_id':jid,'email_all_eligible':False}
    from app.prospecting.policy import configuration as prospecting_configuration
    configuration=prospecting_configuration(configuration)
    c.execute("INSERT INTO scan_campaigns(id,created_by,configuration_json,created_at,target_total,status,source_type,source_metadata,original_prompt,organization_id) VALUES(?,?,?,?,?,'QUEUED',?,?,?,?)",(cid,r['owner'],encoded(configuration),now(),configuration['target'],r['source_type'],encoded({'acquisition_job_id':jid,**origin}),prompt,org))
    from app.workflows.history import capture_settings
    capture_settings(c,cid,configuration)
    c.execute('UPDATE acquisition_jobs SET campaign_id=?,updated_at=? WHERE id=?',(cid,now(),jid))
    return cid

def stage_file(c,actor,name,raw,key):
    name=filename(name);book=Spreadsheet(raw,name);manifest=book.inspect();fingerprint=hashlib.sha256(raw).hexdigest()
    r=create_job(c,'FILE_IMPORT',actor,key,{}, {'filename':name,'sha256':fingerprint,'file_format':manifest['file_format']},status='MAPPING_REVIEW')
    if r['upload_key']:return detail(c,r['id'])
    object_key='audits/acquisition/'+r['id']+'/input'+Path(name).suffix.lower()
    with NamedTemporaryFile(suffix=Path(name).suffix) as f:
        f.write(raw);f.flush();artifact_storage().put(object_key,Path(f.name),'application/octet-stream')
    c.execute('UPDATE acquisition_jobs SET upload_key=?,manifest_json=?,updated_at=? WHERE id=?',(object_key,encoded(manifest),now(),r['id']))
    return detail(c,r['id'])

def source_book(r):
    if not r['upload_key']:raise ImportInvalid('The private source file is unavailable.')
    body=artifact_storage().get(r['upload_key'])
    try:raw=body.read(1_000_001)
    finally:body.close()
    return Spreadsheet(raw,json.loads(r['origin_json']).get('filename','source.csv'))

def inspect_sheet(c,jid,actor,sheet):
    r=job(c,jid,actor)
    if r['status']!='MAPPING_REVIEW':raise HTTPException(409,'Mapping can only be changed before acquisition starts.')
    manifest=source_book(r).inspect(sheet)
    c.execute('UPDATE acquisition_jobs SET manifest_json=?,mapping_json=NULL,updated_at=? WHERE id=?',(encoded(manifest),now(),jid))
    return detail(c,jid)

def approve_import(c,jid,actor,mapping,processing,name,key):
    r=job(c,jid,actor)
    proposed={'processing':processing.model_dump(),'name':name,'approval_key':key}
    previous=json.loads(r['configuration_json'])
    if r['status']!='MAPPING_REVIEW' and 'budgets' in previous:proposed['budgets']=previous['budgets']
    elif r['status']=='MAPPING_REVIEW':
        from app.acquisition.preferences import load
        preferences=load(c)
        if preferences:proposed['budgets']=Budgets.model_validate(preferences.get('budgets',{})).model_dump()
    if r['status']!='MAPPING_REVIEW':
        if json.loads(r['configuration_json'])==proposed and json.loads(r['mapping_json'] or '{}')==mapping.model_dump():return detail(c,jid)
        raise HTTPException(409,'Import was already reviewed or has started.')
    manifest=json.loads(r['manifest_json']);mapping.validate_headers(manifest['headers'])
    c.execute("UPDATE acquisition_jobs SET mapping_json=?,configuration_json=?,status='QUEUED',updated_at=? WHERE id=?",(mapping.model_dump_json(),encoded(proposed),now(),jid))
    create_campaign(c,jid,name or json.loads(r['origin_json']).get('filename') or 'Google Sheets import',target=max(1,manifest['row_count']))
    event(c,jid,'MAPPING_APPROVED','Owner approved column mapping. Valid normalized, deduplicated rows are trusted qualified imports. Analysis and send eligibility remain separate.')
    return detail(c,jid)

def refresh_counts(c,jid,extra=None):
    r=job(c,jid);cid=r['campaign_id'];counts=json.loads(r['counts_json']);counts.update(extra or {})
    usage=c.execute("SELECT COUNT(*) queries,SUM(credits) credits FROM acquisition_requests WHERE job_id=? AND kind='search'",(jid,)).fetchone();counts['queries_run']=usage['queries'];counts['credits_used']=c.execute('SELECT SUM(credits) FROM acquisition_requests WHERE job_id=?',(jid,)).fetchone()[0]
    counts['unreported_credit_requests']=c.execute('SELECT COUNT(*) FROM acquisition_requests WHERE job_id=? AND credits IS NULL',(jid,)).fetchone()[0]
    counts['already_contacted']=c.execute("SELECT COUNT(*) FROM acquisition_issues WHERE job_id=? AND reason='ALREADY_CONTACTED'",(jid,)).fetchone()[0]
    if cid:
        scope='SELECT id FROM pipeline_runs WHERE campaign_id=?'
        row=c.execute('''SELECT COUNT(DISTINCT e.prospect_id) unique_businesses,
          COUNT(DISTINCT CASE WHEN e.was_existing=0 THEN e.prospect_id END) new_businesses,
          COUNT(DISTINCT CASE WHEN e.was_existing=1 THEN e.prospect_id END) existing_businesses
          FROM lead_source_evidence e WHERE e.campaign_id=?''',(cid,)).fetchone();counts.update(dict(row))
        metrics=c.execute('SELECT COALESCE(SUM(websites_processed),0) analyzed,COALESCE(SUM(raw_found),0) candidates FROM pipeline_runs WHERE campaign_id=?',(cid,)).fetchone();counts.update(dict(metrics))
        counts['duplicates']=c.execute('SELECT COUNT(*) FROM businesses WHERE run_id IN ('+scope+') AND is_duplicate=1',(cid,)).fetchone()[0]
        counts['qualified']=c.execute("SELECT COUNT(DISTINCT prospect_id) FROM businesses WHERE run_id IN ("+scope+") AND processing_status='QUALIFIED'",(cid,)).fetchone()[0]
        target=json.loads(r['configuration_json']).get('intent',{}).get('targetQualifiedLeads',c.execute('SELECT target_total FROM scan_campaigns WHERE id=?',(cid,)).fetchone()[0]);counts['target_contactable']=target;counts['remaining']=max(0,target-counts['qualified']);counts['target_reached']=counts['remaining']==0
        counts['shortfall']=counts['remaining']
        counts['issues']=c.execute('SELECT COUNT(*) FROM acquisition_issues WHERE job_id=?',(jid,)).fetchone()[0]
        if r['source_type']=='FIRECRAWL':
            observed=[]
            for request in c.execute("SELECT response_json FROM acquisition_requests WHERE job_id=? AND kind='scrape' AND status='COMPLETED'",(jid,)).fetchall():
                candidate=json.loads(request[0] or '{}').get('candidate')
                if candidate:observed.append(candidate)
            counts['businesses_found']=len(observed);counts['websites_found']=sum(bool(x.get('website')) for x in observed)
            counts['emails_found']=max(sum(bool(x.get('email')) for x in observed),counts['qualified'])
        mode=policy(r['source_type'])
        if mode.trusted_import:
            counts['qualified_imported']=counts['qualified']
            processing=[json.loads(x[0]).get('_processing',{}) for x in c.execute('SELECT field_sources_json FROM lead_source_evidence WHERE campaign_id=?',(cid,)).fetchall()]
            for state,key in [('COMPLETE','analysis_complete'),('FAILED','analysis_failed'),('PENDING','analysis_pending'),('PARTIAL','analysis_partial'),('NOT_AVAILABLE','analysis_not_available')]:counts[key]=sum(x.get('company_information_status')==state for x in processing)
    c.execute('UPDATE acquisition_jobs SET counts_json=?,updated_at=? WHERE id=?',(encoded(counts),now(),jid));return counts

def issue(c,jid,row_number,reason,values=None):
    key=str(uuid.uuid5(uuid.NAMESPACE_URL,jid+':'+str(row_number)+':'+reason+':'+encoded(values or {})))
    c.execute('INSERT INTO acquisition_issues(id,job_id,row_number,reason,values_json,created_at) VALUES(?,?,?,?,?,?) ON CONFLICT(id) DO NOTHING',(key,jid,row_number,reason[:500],encoded(values or {}),now()))

def retry(c,jid,actor):
    r=job(c,jid,actor)
    expired=r['status']=='RUNNING' and r['lease_until'] and r['lease_until']<now()
    if r['status'] not in ('FAILED','DEGRADED') and not expired:raise HTTPException(409,'Only a failed or partial acquisition can be retried.')
    if r['lease_until'] and r['lease_until']>now():raise HTTPException(409,'The acquisition worker is still active; wait for its lease to expire.')
    c.execute("UPDATE acquisition_jobs SET status='QUEUED',error_code=NULL,error_message=NULL,execution_name=NULL,finished_at=NULL,updated_at=? WHERE id=?",(now(),jid))
    event(c,jid,'RETRY_REQUESTED','Explicit retry requested; existing canonical leads and completed batches are preserved.')
    return detail(c,jid)
